#!/usr/bin/env python3
"""Validate a complete Daily News edition, then update manifests WITHOUT rewriting approved UI.

This preserves the existing 3-file publication gate. New HTML-only editions may be
listed in the UI catalog with an explicit incomplete-PDF status, but MUST NOT enter
issues.json (the complete publication manifest) until all 3 files pass QA.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

FEATURES = ['体育与周末回顾', '科技专题', '家庭与成长', '文化生活与周末指南', '财经与产业观察', '文化与趣味发现', 'Weekend Special｜深度专题、东西方哲学、英文精读']
CATEGORIES = ['社会', '科技', '社会', '文化', '财经', '文化', '专题']


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
    if not item['title'].strip() or item['feature'] != FEATURES[day.weekday()]:
        raise ValueError('Title/weekday feature is invalid')
    cutoff=dt.datetime.fromisoformat(item['cutoff'])
    if cutoff.utcoffset()!=dt.timedelta(hours=8) or cutoff.date()!=day:
        raise ValueError('Cutoff must be the issue date with +08:00 offset')
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
        existing={x['date']:x for x in before.get('issues',[]) if re.fullmatch(r'\d{4}-\d{2}-\d{2}',x.get('date',''))}
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
        category=old.get('category') or CATEGORIES[day.weekday()]
        feature=approved.get('feature') or old.get('feature') or FEATURES[day.weekday()]
        title=approved.get('title') or old.get('title') or f'{date} · {feature}'
        entry={
            'date':date,'title':title,'feature':feature,'category':category,
            'summary':old.get('summary') or '已发布期刊：完整正文、来源与解读请查看原刊。',
            'html':f'issues/{date}/index.html',
            'pdf_full':f'issues/{date}/完整版.pdf' if valid_pdf(folder/'完整版.pdf') else None,
            'pdf_podcast':f'issues/{date}/播客版.pdf' if valid_pdf(folder/'播客版.pdf') else None,
            'stories':old.get('stories',[]),
        }
        entries.append(entry)
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
    args=parser.parse_args()
    date=dt.date.fromisoformat(args.date)
    item={'date':args.date,'title':args.title,'feature':FEATURES[date.weekday()],'cutoff':args.cutoff}
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