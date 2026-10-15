#!/usr/bin/env python3
"""Build the homepage/archive after a complete, reviewed issue is staged. No scheduler or credentials."""
import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path

FEATURES = ['体育与周末回顾', '科技专题', '家庭与成长', '文化生活与周末指南', '财经与产业观察', '文化与趣味发现', 'Weekend Special｜深度专题、东西方哲学、英文精读']
WEEKDAYS = '一二三四五六日'

def validate(root, item):
    day = dt.date.fromisoformat(item['date'])
    if item['date'] != day.isoformat():
        raise ValueError('Date must be YYYY-MM-DD')
    if day > dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date():
        raise ValueError('Cannot publish a future issue')
    if not item['title'].strip() or item['feature'] != FEATURES[day.weekday()]:
        raise ValueError('Title/weekday feature is invalid')
    cutoff = dt.datetime.fromisoformat(item['cutoff'])
    if cutoff.utcoffset() != dt.timedelta(hours=8) or cutoff.date() != day:
        raise ValueError('Cutoff must be the issue date with +08:00 offset')
    folder = root / 'issues' / item['date']
    for name in ('index.html', '完整版.pdf', '播客版.pdf'):
        path = folder / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'Missing/invalid publication file: {path}')
        data = path.read_bytes()
        if name.endswith('.pdf') and (not data.startswith(b'%PDF-') or b'%%EOF' not in data[-2048:]):
            raise ValueError(f'Invalid PDF: {path}')
    body = (folder / 'index.html').read_text(encoding='utf-8')
    if '<html' not in body.lower() or '</html>' not in body.lower():
        raise ValueError('Incomplete HTML')
    return item

def build(root, items):
    if len({x['date'] for x in items}) != len(items):
        raise ValueError('Duplicate issue dates')
    for x in items:
        validate(root, x)
    items = sorted(items, key=lambda x:x['date'], reverse=True)
    if not items:
        raise ValueError('No issues')
    home = (root / 'index.html').read_text(encoding='utf-8')
    style = re.search(r'<style>(.*?)</style>', home, re.S).group(1)
    e = html.escape
    def page(title, content):
        return '<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(title)+'</title><style>'+style+'</style></head><body><main>'+content+'</main></body></html>'
    def card(x, latest=False):
        d=dt.date.fromisoformat(x['date']); path='issues/'+x['date']+'/'
        lead='最新期刊' if latest else '历史期刊'
        return '<article><div class="sub">'+lead+' · '+x['date']+' · 星期'+WEEKDAYS[d.weekday()]+'</div><h2>'+e(x['title'])+'</h2><p>'+e(x['feature'])+'</p><a href="'+path+'index.html">直接在线阅读 →</a><p><a href="'+path+'完整版.pdf" download>完整 PDF ↓</a> <a href="'+path+'播客版.pdf" download>中国平台友好 PDF ↓</a></p></article>'
    intro='<div class="eyebrow">AMO\'S LEARNING LAB</div><h1>Daily News</h1><p>每日五类要闻 · 每周轮换专题 · 周末深度特刊</p>'
    latest=items[0]
    content=intro+card(latest, True)+'<article><h2><a href="archive.html">历史归档 →</a></h2><p>按日期阅读已发布期刊和下载 PDF。</p></article><p class="sub">最新可用期刊：'+latest['date']+'。每日 10:00（北京时间）为开始制作时间；通过核验后再发布。日期以实际已发布期刊为准。</p><p class="sub">新闻反馈与个人数据不会公开发布。</p>'
    archive='<div class="eyebrow">DAILY NEWS · ARCHIVE</div><h1>历史归档</h1><a href="index.html">← 首页</a><p>仅列已经发布的期刊。</p>'+''.join(card(x) for x in items)
    archive+='<article><h2>每周专题排期</h2><p>以下为编辑排期，不表示各期已经发布；重大新闻不因排期延迟。</p><ul>'+''.join('<li>周'+WEEKDAYS[i]+' · '+e(f)+'</li>' for i,f in enumerate(FEATURES))+'</ul></article>'
    # All validation/rendering finishes before writing any output.
    result={'index.html':page('Amo｜Daily News',content),'archive.html':page('历史归档｜Daily News',archive),'issues.json':json.dumps({'version':1,'issues':items},ensure_ascii=False,indent=2)+'\n'}
    for name, text in result.items():
        (root/name).write_text(text,encoding='utf-8')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--date',required=True)
    p.add_argument('--title',required=True)
    p.add_argument('--cutoff',required=True,help='Example: 2026-10-15T11:30:00+08:00')
    a=p.parse_args();day=dt.date.fromisoformat(a.date)
    item={'date':a.date,'title':a.title,'feature':FEATURES[day.weekday()],'cutoff':a.cutoff}
    items=json.loads((a.root/'issues.json').read_text())['issues']
    previous=next((x for x in items if x['date']==a.date),None)
    if previous and previous!=item:
        raise ValueError('Existing date has different metadata. Review before changing a published issue.')
    if not previous:items.append(item)
    build(a.root,items)
    print('Prepared homepage, archive and manifest. Not uploaded. Content/file/interaction/privacy QA remains mandatory.')

if __name__=='__main__':
    main()
