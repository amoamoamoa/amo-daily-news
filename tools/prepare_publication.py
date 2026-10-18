#!/usr/bin/env python3
"""Validate a complete Daily News edition, then update manifests WITHOUT rewriting approved UI.

This preserves the existing 3-file publication gate. Historical HTML-only editions
retain their catalog entries; new dates require a complete edition and independently
verified story metadata before either manifest is updated.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

FEATURES = ['体育与周末回顾', '科技专题', '家庭与成长', '文化生活与周末指南', '财经与产业观察', '文化与趣味发现', 'Weekend Special｜深度专题、东西方哲学、英文精读']
CATEGORIES = ['社会', '科技', '社会', '文化', '财经', '文化', '专题']
STORY_CATEGORIES = {'国际', '国内', '长三角', '科技', '财经', '专题'}
ARTS = {'world', 'city', 'ai', 'finance', 'science', 'book'}

# Weekend v2.1 begins with the NEXT weekend; preserve prior approved issues.
# FEATURES and old manifests remain the historical baseline through 2026-10-18.
WEEKEND_V21_FROM = dt.date(2026, 10, 24)
WEEKEND_V21 = {
    5: 'Weekend Special｜两篇独立深度专题',
    6: 'Weekend Special｜深度专题＋英文精读',
}

def feature_for(day):
    """Prospective labels only; existing editions retain their recorded feature."""
    if day >= WEEKEND_V21_FROM and day.weekday() in WEEKEND_V21:
        return WEEKEND_V21[day.weekday()]
    return FEATURES[day.weekday()]



def read_metadata(folder, title):
    """Read editorially verified data, never infer news from HTML or filenames."""
    path = folder / 'stories.json'
    if not path.exists() and not path.is_symlink():
        return None  # Legacy editions retain their existing catalog metadata.
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Invalid story metadata file: {path}')
    data = json.loads(path.read_text(encoding='utf-8'))
    fields = {'schema', 'date', 'title', 'category', 'summary', 'stories'}
    if not isinstance(data, dict) or set(data) != fields:
        raise ValueError(f'Unexpected/missing story metadata fields: {path}')
    if type(data['schema']) is not int or data['schema'] != 1:
        raise ValueError(f'Unsupported story metadata schema: {path}')
    if data['date'] != folder.name or data['title'] != title:
        raise ValueError(f'Story metadata date/title mismatch: {path}')
    for key in ('title', 'category', 'summary'):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f'Empty/invalid metadata {key}: {path}')
    if data['category'] not in set(CATEGORIES):
        raise ValueError(f'Unsupported archive category: {path}')
    if not isinstance(data['stories'], list) or not data['stories']:
        raise ValueError(f'Nonempty verified stories required: {path}')
    seen = set()
    for story in data['stories']:
        if not isinstance(story, dict) or set(story) != {'id', 'cat', 'title', 'art'}:
            raise ValueError(f'Unexpected/missing story fields: {path}')
        if not all(isinstance(story[k], str) and story[k].strip() for k in story):
            raise ValueError(f'Empty/invalid story field: {path}')
        sid = story['id']
        if not re.fullmatch(re.escape(folder.name) + r'-[A-Za-z0-9_-]+', sid) or sid in seen:
            raise ValueError(f'Invalid/duplicate story id: {path}')
        if story['cat'] not in STORY_CATEGORIES or story['art'] not in ARTS:
            raise ValueError(f'Unsupported story category/art: {path}')
        seen.add(sid)
    return data


def valid_pdf(path):
    if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
        return False
    content = path.read_bytes()
    return content.startswith(b'%PDF-') and b'%%EOF' in content[-2048:]


def validate(root, item):
    day=dt.date.fromisoformat(item['date'])
    if item['date'] != day.isoformat():
        raise ValueError('Date must be YYYY-MM-DD')
    if day > dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date():
        raise ValueError('Cannot publish a future issue')
    if not item['title'].strip() or item['feature'] != feature_for(day):
        raise ValueError('Title/weekday feature is invalid')
    cutoff=dt.datetime.fromisoformat(item['cutoff'])
    if cutoff.utcoffset()!=dt.timedelta(hours=8):
        raise ValueError('Cutoff must use the +08:00 offset')
    if cutoff.date()!=day:
        if not item.get('backfill') or cutoff.date()<day:
            raise ValueError('Later cutoff requires explicit retrospective backfill')
    if cutoff > dt.datetime.now(dt.timezone(dt.timedelta(hours=8))):
        raise ValueError('Cannot claim a future verification cutoff')
    folder=root/'issues'/item['date']
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError(f'Missing issue folder: {folder}')
    for name in ('index.html','完整版.pdf','播客版.pdf'):
        path=folder/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size==0:
            raise ValueError(f'Missing/invalid publication file: {path}')
        if name.endswith('.pdf') and not valid_pdf(path):
            raise ValueError(f'Invalid PDF: {path}')
    html=(folder/'index.html').read_text(encoding='utf-8')
    if '<html' not in html.lower() or '</html>' not in html.lower():
        raise ValueError('Incomplete HTML')
    return item


def build_catalog(root, completed):
    """Collect verified existing HTML paths; NEVER claim PDF downloads that aren't valid."""
    catalog_path=root/'site'/'catalog.json'
    existing={}
    if catalog_path.exists():
        before=json.loads(catalog_path.read_text(encoding='utf-8'))
        for entry in before['issues']:
            date = entry['date']
            if date != dt.date.fromisoformat(date).isoformat() or date in existing:
                raise ValueError('Invalid/duplicate existing catalog date')
            existing[date] = entry
    entries=[]
    issue_dir=root/'issues'
    for folder in sorted(issue_dir.iterdir(),reverse=True) if issue_dir.exists() else []:
        if not folder.is_dir() or folder.is_symlink() or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',folder.name):
            continue
        page=folder/'index.html'
        if not page.is_file() or page.is_symlink() or not page.stat().st_size:
            continue
        body=page.read_text(encoding='utf-8')
        if '<html' not in body.lower() or '</html>' not in body.lower():
            continue
        date=folder.name;day=dt.date.fromisoformat(date)
        approved=completed.get(date,{});old=existing.get(date,{})
        if date not in existing and date not in completed:
            raise ValueError(f'New issue must pass the complete publication gate: {date}')
        category=old.get('category') or CATEGORIES[day.weekday()]
        feature=approved.get('feature') or old.get('feature') or feature_for(day)
        title=approved.get('title') or old.get('title') or f'{date} · {feature}'
        metadata=read_metadata(folder,title)
        if metadata is None and date not in existing:
            raise ValueError(f'New issue requires verified metadata: {folder}/stories.json')
        if metadata and old.get('stories') and any(
            metadata[key] != old.get(key) for key in ('title','category','summary','stories')
        ):
            raise ValueError(f'Published story metadata differs; review before changing: {date}')
        public=metadata or old
        entry={
            'date':date,'title':title,'feature':feature,'category':public.get('category') or category,
            'summary':public.get('summary') or '已发布期刊：完整正文、来源与解读请查看原刊。',
            'html':f'issues/{date}/index.html',
            'pdf_full':f'issues/{date}/完整版.pdf' if valid_pdf(folder/'完整版.pdf') else None,
            'pdf_podcast':f'issues/{date}/播客版.pdf' if valid_pdf(folder/'播客版.pdf') else None,
            'stories':public.get('stories',[]),
        }
        entries.append(entry)
    missing=(set(existing) | set(completed)) - {x['date'] for x in entries}
    if missing:
        raise ValueError(f'Historical issue HTML missing/invalid; refusing to drop: {sorted(missing)}')
    return {'schema':1,'note':'由原发布流程核验文件后更新；没有生成占位期刊或虚假 PDF 链接。','issues':entries}


def build(root, items):
    """Validate all complete editions before any manifest writes; preserve approved HTML."""
    if len({x['date'] for x in items})!=len(items):
        raise ValueError('Duplicate issue dates')
    for item in items:
        validate(root,item)
    for required in ('index.html','archive.html','assets/app.js'):
        if not (root/required).is_file():
            raise ValueError(f'Approved UI file missing: {root/required}')
    home=(root/'index.html').read_text(encoding='utf-8')
    if 'id="catalog-fallback"' not in home or 'id="page-board"' not in home:
        raise ValueError('Approved UI has been unexpectedly replaced')
    sorted_items=sorted(items,key=lambda i:i['date'],reverse=True)
    catalogue=build_catalog(root,{x['date']:x for x in sorted_items})
    # Read/validate and render everything before writing either manifest.
    output={
        'issues.json':json.dumps({'version':1,'issues':sorted_items},ensure_ascii=False,indent=2)+'\n',
        'site/catalog.json':json.dumps(catalogue,ensure_ascii=False,indent=2)+'\n',
    }
    for name,text in output.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--date',required=True)
    parser.add_argument('--title',required=True)
    parser.add_argument('--cutoff',required=True)
    parser.add_argument('--backfill',action='store_true',help='Explicit retrospective issue: allow verification after issue date')
    args=parser.parse_args()
    date=dt.date.fromisoformat(args.date)
    item={'date':args.date,'title':args.title,'feature':feature_for(date),'cutoff':args.cutoff}
    if args.backfill:
        item['backfill']=True
    manifest=args.root/'issues.json'
    items=json.loads(manifest.read_text(encoding='utf-8'))['issues']
    prev=next((x for x in items if x['date']==args.date),None)
    if prev and prev!=item:
        raise ValueError('Existing date has different metadata. Review before changing a published issue.')
    if not prev:
        items.append(item)
    build(args.root,items)
    print('Validated full edition and refreshed manifests. Approved UI preserved. Not uploaded.')

if __name__=='__main__':main()
