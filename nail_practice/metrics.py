"""Transparent descriptive statistics only. No inferred demand/purchase indices."""
from __future__ import annotations
from collections import Counter,defaultdict
from datetime import date,timedelta
from statistics import mean,median

def average(nums):return round(mean(nums),1) if nums else None
def middle(nums):return round(median(nums),1) if nums else None
def ratio(a,b):return round(100*a/b,2) if b else None

def overview(posts,accounts,media_count,country='all'):
    ps=[p for p in posts if country=='all' or p['country']==country]
    ac=[a for a in accounts if country=='all' or a['country']==country]
    valid=[p['reactions'] for p in ps if p['reactions'] is not None]
    reels=sum(p['product_type']=='REELS' for p in ps)
    return {'selection':country,'stats':{
      'accounts':len(ac),'collected_accounts':sum(a['collection_status']=='collected' for a in ac),
      'posts':len(ps),'media':media_count if country=='all' else None,
      'reaction_available':len(valid),'reaction_missing':len(ps)-len(valid),
      'reaction_coverage_pct':ratio(len(valid),len(ps)),
      'reels':reels,'reels_pct':ratio(reels,len(ps)),
      'avg_reactions_observed':average(valid),'median_reactions_observed':middle(valid),
    },'media_type':dict(Counter(p['media_type'] for p in ps)),
    'week_counts':weekly(ps),
    'hours':[{'hour':hr,'count':sum(p['hour_kst']==hr for p in ps),'median_reaction_observed':middle([p['reactions'] for p in ps if p['hour_kst']==hr and p['reactions'] is not None])} for hr in range(24) if any(p['hour_kst']==hr for p in ps)],
    'date_range':{'start':min((p['post_date'] for p in ps),default=None),'end':max((p['post_date'] for p in ps),default=None)},
    'notes':['표본 편향: 계정별 최근 1/5/10건이 혼합되어 국가지표의 시장 대표성이 없습니다.',
             '반응 평균과 중앙값은 좋아요·댓글이 모두 있는 게시물만 사용합니다.',
             '조회수·디자인 태그·수요/성과지수 없음. 추가 분석 미실시.']}

def weekly(ps):
    if not ps:return []
    end=max(date.fromisoformat(p['post_date']) for p in ps)
    anchor=end-timedelta(days=end.weekday())
    vals=Counter(date.fromisoformat(p['post_date'])-timedelta(days=date.fromisoformat(p['post_date']).weekday()) for p in ps)
    return [{'week':(anchor-timedelta(weeks=i)).isoformat(),'posts':vals[anchor-timedelta(weeks=i)]} for i in range(12,-1,-1)]

def countries(posts,accounts,media):
    return [{'country':code,'name':{'KR':'한국','US':'미국','JP':'일본'}[code],
             **overview(posts,accounts,media,code)['stats'],
             'media':sum(m['country']==code for m in media)} for code in ['KR','US','JP']]

def top_posts(posts,country='all',page=1,per_page=15):
    valid=[p for p in posts if p['reactions'] is not None and (country=='all' or p['country']==country)]
    valid.sort(key=lambda p:(-p['reactions'],p['post_id']))
    top=valid[:20]
    return {'items':[{key:p[key] for key in ('post_id','account_key','country','post_date','media_type','product_type','likes','comments','reactions','media_rows')} for p in top[(page-1)*per_page:page*per_page]],
            'total':len(top),'page':page,'pages':max(1,(len(top)+per_page-1)//per_page),'per_page':per_page,
            'excluded_missing_reactions':sum(p['reactions'] is None for p in posts if country=='all' or p['country']==country),
            'note':'반응값이 확보된 게시물만 순위에 포함. 원본 성과지수·구매확률은 미산출.'}
