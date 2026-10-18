"""Pure, explicitly *demonstration-only* statistical rules.
Not recovered from any reference site's backend.
"""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import date,timedelta
from math import ceil
from statistics import median,mean


def mid(xs):
    return round(median(xs),2) if xs else None


def avg(xs):
    return round(mean(xs),1) if xs else None


def positive_ratio(n,d):
    return round(100*n/d) if d else 0


def after(p,cutoff):
    return date.fromisoformat(p['posted_at']) >= cutoff


def report_total(raw):
    return {'collected':len(raw),'analyzed':sum(p['analyzed'] for p in raw),'reels':sum(p['medium']=='reel' for p in raw)}


def brand_index(rows,cutoff):
    """Demo 4-week ratio = median(reactions last 28 days)/median(all analyzed reactions)."""
    all_reactions=[p['reactions'] for p in rows]
    current=[p['reactions'] for p in rows if after(p,cutoff)]
    if len(current)<3 or not all_reactions or not median(all_reactions):return None
    return round(median(current)/median(all_reactions),2)


def get_brand_summary(all_posts,brand_rows,end_date):
    begin=end_date-timedelta(days=27)
    out=[]
    for b in brand_rows:
        raw=[p for p in all_posts if p['brand']==b['slug']]
        a=[p for p in raw if p['analyzed']]
        v=[p['reactions'] for p in a]
        recent=[p for p in a if after(p,begin)]
        with_views=sum(p['views'] is not None for p in raw)
        out.append({**b,'collected':len(raw),'analyzed':len(a),'recent_count':len(recent),
                    'reaction_median':mid(v),'reaction_mean':avg(v),'four_week_index':brand_index(a,begin),
                    'view_coverage':positive_ratio(with_views,len(raw))})
    return out


def dashboard(all_posts,brand_rows,end_date,selection='all'):
    chosen=[p for p in all_posts if selection=='all' or p['brand']==selection]
    analyzed=[p for p in chosen if p['analyzed']]
    summaries=get_brand_summary(all_posts,brand_rows,end_date)
    reactions=[p['reactions'] for p in analyzed]
    bases={b['slug']:b['reaction_median'] for b in summaries}
    above=sum(p['reactions']>bases[p['brand']] for p in analyzed if bases[p['brand']] is not None)
    total=report_total(chosen)
    total.update({'collection_rate':positive_ratio(total['analyzed'],total['collected']),
                  'reels_share_collected':positive_ratio(total['reels'],total['collected']),
                  'reaction_average':avg(reactions),'above_brand_baseline':above,
                  'above_baseline_ratio':positive_ratio(above,len(analyzed))})
    weeks=[]
    for index in range(12,-1,-1):
        first=end_date-timedelta(days=end_date.weekday()+index*7)
        last=first+timedelta(days=6)
        row={'week':first.isoformat(),'label':first.strftime('%m/%d')}
        for b in brand_rows:
            row[b['slug']]=sum(first<=date.fromisoformat(p['posted_at'])<=last and p['brand']==b['slug'] for p in analyzed)
        weeks.append(row)
    fmt=defaultdict(list)
    by_hour=defaultdict(list)
    for p in analyzed:
        fmt[(p['medium'],p['purpose'])].append(p['reactions'])
        by_hour[p['hour_kst']].append(p['reactions'])
    media_label={'reel':'릴스','carousel':'캐러셀','image':'단일 이미지'}
    formats=[{'name':f'{media_label[k[0]]} · {k[1]}','mean':avg(v),'count':len(v)} for k,v in fmt.items()]
    formats.sort(key=lambda d:(-d['mean'],d['name']))
    return {'selection':selection,'summary':total,'weeks':weeks,'formats':formats[:6],
            'hours':[{'hour':h,'median':mid(by_hour[h])} for h in range(8,23) if by_hour[h]],
            'types':[{'name':'직접 시술','count':sum(p['treatment']=='direct' for p in analyzed)},
                     {'name':'시트형','count':sum(p['treatment']=='sheet' for p in analyzed)}],
            'selected_brand':next((b for b in summaries if b['slug']==selection),None),
            'brands':summaries}


def compare(all_posts,brand_rows,end_date):
    return {'brands':get_brand_summary(all_posts,brand_rows,end_date),
            'formula_note':'데모 4주 지수 = 최근 28일 분석 게시물 반응 중앙값 ÷ 전체 분석 기간 반응 중앙값 (최근 표본 3건 미만은 결측). 원본 수식 아님.'}


def tag_summary(all_posts,tags,links,category,ending,page,per_page):
    # Observed: tags are NOT scoped by the selected sidebar brand.
    analyzed={p['id']:p for p in all_posts if p['analyzed']}
    baseline=mid([p['reactions'] for p in analyzed.values()])
    grouped=defaultdict(list)
    for rel in links:
        if rel['post_id'] in analyzed:
            grouped[rel['tag_id']].append(analyzed[rel['post_id']])
    cur_start=ending-timedelta(days=27)
    prev_start=ending-timedelta(days=83)
    results=[]
    for t in tags:
        if category!='all' and t['category']!=category:continue
        ps=grouped[t['id']]
        demand=round(mid([p['reactions'] for p in ps])/baseline,2) if len(ps)>=3 and baseline else None
        recent=sum(after(p,cur_start) for p in ps)
        older=sum(prev_start<=date.fromisoformat(p['posted_at'])<cur_start for p in ps)
        trend=round((recent/4)/(older/8),2) if older and len(ps)>=3 else None
        label='표본 부족' if demand is None else '수요 높음' if demand>=1.25 else '수요 낮음' if demand<.8 else '보통'
        results.append({'name':t['name'],'category':t['category'],'posts':len(ps),'demand_index':demand,'trend_4v8':trend,'label':label})
    results.sort(key=lambda x: (x['demand_index'] is None,-(x['demand_index'] or 0),-x['posts'],x['name']))
    start=(page-1)*per_page
    return {'items':results[start:start+per_page],'total':len(results),'page':page,'per_page':per_page,'pages':max(1,ceil(len(results)/per_page)),
            'category':category,'formula_note':'데모 수요지수 = 태그 게시물 반응 중앙값 ÷ 전체 분석 게시물 반응 중앙값 (3건 미만 결측). 데모 4주÷8주 = 최근 4주 주당 건수 ÷ 이전 8주 주당 건수 (분모 0이면 결측). 원본 공식 미확인.'}


def top_posts(all_posts,brand,page,per_page):
    a=[p for p in all_posts if p['analyzed'] and (brand=='all' or p['brand']==brand)]
    a.sort(key=lambda p:(-p['reactions'],-p['id']))
    top=a[:20]
    start=(page-1)*per_page
    return {'items':[{'id':p['id'],'posted_at':p['posted_at'],'brand':p['brand_name'],'brand_slug':p['brand'],
                      'medium':p['medium'],'purpose':p['purpose'],'reactions':p['reactions'],
                      'views':p['views'],'performance_index':None, # original scoring unavailable: explicit placeholder
                      'url':p['url']} for p in top[start:start+per_page]],
            'total':len(top),'page':page,'per_page':per_page,'pages':max(1,ceil(len(top)/per_page)),
            'formula_note':'게시물별 성과지수는 원본 산식 미확인으로 미구현(null). 데모에서는 반응 수 내림차순으로 정렬.'}
