"""Collect dated official observations; keep last good values on partial failure."""
from __future__ import annotations
import argparse, concurrent.futures, csv, datetime as dt, html, io, json, math, re, sys, time, unicodedata
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
UTC=dt.timezone.utc

class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.skip=0; self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
        if tag=='a': self.links.append(dict(attrs).get('href',''))
        if tag in ('p','div','tr','br','li','h1','h2','h3'): self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
    def text(self):return unicodedata.normalize('NFKC',html.unescape(' '.join(self.parts)))

def fetch(url):
    for attempt in range(2):
        try:
            with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (Knowledge Assist economic education; official source attribution)','Accept':'text/html,text/csv,application/pdf,*/*'}),timeout=25) as r:
                raw=r.read(8_000_001)
                if len(raw)>8_000_000:raise ValueError('response too large')
                charset=r.headers.get_content_charset()
                return raw,charset
        except Exception:
            if attempt:raise
            time.sleep(1)

def document(url):
    raw,enc=fetch(url)
    if not enc:
        m=re.search(br'charset\s*=\s*["\']?([A-Za-z0-9_-]+)',raw[:3000],re.I)
        enc=m.group(1).decode() if m else 'utf-8'
    try:s=raw.decode(enc)
    except (UnicodeError,LookupError):s=raw.decode('cp932')
    t=Text();t.feed(s)
    return t,s

def valid_date(s):
    d=dt.date.fromisoformat(s)
    if d>dt.datetime.now(UTC).date()+dt.timedelta(days=1):raise ValueError('future observation')
    return s

def metric(value,date,source,unit,*,history=None,frequency='日次',released=None):
    if not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('non-finite observation')
    out={'value':value,'date':valid_date(date),'source':source,'unit':unit,'frequency':frequency,'fetched_at':dt.datetime.now(UTC).isoformat(timespec='seconds'),'status':'ok'}
    if history is not None:out['history']=history[-370:]
    if released:out['released']=valid_date(released)
    return out

def fred_rows(payload):
    # FRED provides either plain table data or a table-data HTML page. Never
    # interpret dates in script assets, release times or unrelated page chrome.
    txt=payload
    if '<html' in payload.lower():
        t=Text();t.feed(payload);txt=t.text()
    values={}
    for date,value in re.findall(r'(?:#|\n|\s)(\d{4}-\d{2}-\d{2})\s*(?:\||\s)\s*(-?\d+(?:\.\d+)?)(?=\s|$|#)',txt):
        try:
            valid_date(date);v=float(value)
            if math.isfinite(v):values[date]=v
        except ValueError:pass
    if len(values)<5:raise ValueError('FRED time-series table not found')
    return [{'date':d,'value':v} for d,v in sorted(values.items())]

def fred(series,unit,limits):
    source='https://fred.stlouisfed.org/series/'+series
    raw,enc=fetch('https://fred.stlouisfed.org/data/'+series+'.txt')
    payload=raw.decode(enc or 'utf-8')
    if series not in payload:raise ValueError('series identifier mismatch')
    rows=fred_rows(payload);last=rows[-1]
    if not limits[0]<=last['value']<=limits[1]:raise ValueError('observation outside valid range')
    return metric(last['value'],last['date'],source,unit,history=rows)

def japan_yield():
    url='https://www.mof.go.jp/jgbs/reference/interest_rate/jgbcm.csv'
    raw,_=fetch(url);rows=list(csv.reader(io.StringIO(raw.decode('cp932'))))
    header=next((r for r in rows if r and r[0].strip()=='基準日'),None)
    if not header or '10年' not in header:raise ValueError('MOF header changed')
    idx=header.index('10年');out=[]
    for r in rows:
        if len(r)<=idx:continue
        m=re.fullmatch(r'([RHS])(\d+)\.(\d+)\.(\d+)',r[0].strip())
        if not m:continue
        era,y,mo,d=m.groups();year={'R':2018,'H':1988,'S':1925}[era]+int(y)
        try:date=dt.date(year,int(mo),int(d)).isoformat();v=float(r[idx]);valid_date(date)
        except ValueError:continue
        if not -5<v<25:raise ValueError('MOF yield outside range')
        out.append({'date':date,'value':v})
    if not out:raise ValueError('MOF data missing')
    out.sort(key=lambda x:x['date']);return metric(out[-1]['value'],out[-1]['date'],url,'%',history=out)

def japan_cpi():
    url='https://www.stat.go.jp/data/cpi/sokuhou/tsuki/index-z.html'
    t,_=document(url);s=re.sub(r'\s+',' ',t.text())
    m=re.search(r'全国\s*(\d{4})年.*?(\d{1,2})月分\s*\((\d{4})年(\d{1,2})月(\d{1,2})日公表\)',s)
    if not m:raise ValueError('Japan CPI observation month not found')
    y,mo,ry,rm,rd=map(int,m.groups());date=f'{y:04}-{mo:02}-01';released=f'{ry:04}-{rm:02}-{rd:02}'
    points=s[s.index('ポイント'):]
    vals=re.findall(r'前年同月比は\s*([\d.]+)\s*%の(上昇|下落)',points)
    if len(vals)!=3:raise ValueError('Japan CPI three definitions not found')
    values=[float(v)*(1 if sign=='上昇' else -1) for v,sign in vals]
    return {k:metric(v,date,url,'%',frequency='月次・前年比',released=released) for k,v in zip(('jp_cpi','jp_core','jp_core_energy'),values)}

def us_cpi():
    url='https://www.bls.gov/news.release/cpi.nr0.htm';t,_=document(url);s=re.sub(r'\s+',' ',t.text())
    names={n:i+1 for i,n in enumerate(['January','February','March','April','May','June','July','August','September','October','November','December'])}
    m=re.search(r'CONSUMER PRICE INDEX\s*[-–]\s*([A-Z]+)\s+(20\d{2})',s)
    if not m:raise ValueError('BLS reference month missing')
    month=m.group(1).title();date=f'{int(m.group(2)):04}-{names[month]:02}-01'
    body=s[m.end():]
    # The last table column gives the non-seasonally adjusted annual change.
    # BLS text identifies the same figure explicitly; monthly changes are never
    # substituted for annual changes.
    total=re.search(r'Over the last 12 months, the all items index (increased|decreased) ([\d.]+) percent',body,re.I)
    core=re.search(r'all items less food and energy index (rose|increased|fell|decreased) ([\d.]+) percent over the year',body,re.I)
    if not total or not core:raise ValueError('BLS annual CPI definitions not found')
    tv=float(total[2])*(-1 if total[1].lower()=='decreased' else 1);cv=float(core[2])*(-1 if core[1].lower() in ('fell','decreased') else 1)
    return {k:metric(v,date,url,'%',frequency='月次・前年比') for k,v in [('us_cpi',tv),('us_core',cv)]}

def boj_policy():
    from pypdf import PdfReader
    year=dt.datetime.now(UTC).year
    candidates=[]
    # At the turn of the year the current year's list may not contain a meeting.
    for y in (year,year-1):
        url=f'https://www.boj.or.jp/mopo/mpmdeci/state_{y}/index.htm'
        try:t,_=document(url)
        except Exception:continue
        for link in t.links:
            m=re.search(r'/mpr_(20\d{2})/k(\d{2})(\d{2})(\d{2})a\.pdf$',link)
            if m:
                y,yy,mo,d=map(int,m.groups());date=f'{y:04}-{mo:02}-{d:02}'
                try:valid_date(date)
                except ValueError:continue
                candidates.append((date,urljoin(url,link)))
        if candidates:break
    if not candidates:raise ValueError('BOJ policy document missing')
    date,url=max(candidates);raw,_=fetch(url)
    text=unicodedata.normalize('NFKC',' '.join(p.extract_text() or '' for p in PdfReader(io.BytesIO(raw)).pages[:2]))
    text=re.sub(r'\s+','',text)
    # Failure on a changed monetary-policy regime preserves the last good rate.
    m=re.search(r'無担保コールレート\(オーバーナイト物\)を、?([\d.]+)%程度で推移するよう',text)
    if not m:raise ValueError('BOJ target policy rate not found; review new statement')
    return metric(float(m[1]),date,url,'%',frequency='政策決定日')

def collect(previous=None):
    prev=previous or {};metrics=json.loads(json.dumps(prev.get('metrics',{})));errors={}
    tasks={
      'fx':lambda:fred('DEXJPUS','円／ドル',(1,1000)),
      'us10':lambda:fred('DGS10','%',(-5,30)),
      'brent':lambda:fred('DCOILBRENTEU','ドル／バレル',(-100,1000)),
      'wti':lambda:fred('DCOILWTICO','ドル／バレル',(-100,1000)),
      'us_policy_low':lambda:fred('DFEDTARL','%',(0,30)),
      'us_policy_high':lambda:fred('DFEDTARU','%',(0,30)),
      'jp10':japan_yield,'japan_cpi':japan_cpi,'us_cpi_release':us_cpi,'jp_policy':boj_policy,
    }
    groups={'japan_cpi':['jp_cpi','jp_core','jp_core_energy'],'us_cpi_release':['us_cpi','us_core']}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        future={pool.submit(fn):k for k,fn in tasks.items()}
        for f in concurrent.futures.as_completed(future):
            k=future[f]
            try:
                value=f.result();fresh=value if k in groups else {k:value}
                for name,item in fresh.items():
                    old=metrics.get(name)
                    if old and item['date']<old['date']:raise ValueError('upstream observation regressed')
                metrics.update(fresh)
            except Exception as e:
                errors[k]=f'{type(e).__name__}: {str(e)[:180]}'
                for name in groups.get(k,[k]):
                    if name in metrics:metrics[name]['status']='retained'
    # A policy range is one paired observation, never a mix of different days.
    lo,hi=metrics.get('us_policy_low'),metrics.get('us_policy_high')
    if lo and hi and (lo['date']!=hi['date'] or lo['value']>hi['value']):
        errors['us_policy_pair']='policy range mismatch'
        for name in ('us_policy_low','us_policy_high'):
            if name in prev.get('metrics',{}):metrics[name]=dict(prev['metrics'][name],status='retained')
            else:metrics.pop(name,None)
    now=dt.datetime.now(UTC).isoformat(timespec='seconds')
    return {'schema_version':1,'attempted_at':now,'metrics':metrics,'errors':errors,'mode':'official-public-observations','stock_indices':'official_links_only'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'data/latest.json');parser.add_argument('--strict',action='store_true');args=parser.parse_args()
    previous=json.loads(args.output.read_text()) if args.output.exists() else None
    result=collect(previous);args.output.parent.mkdir(parents=True,exist_ok=True)
    temp=args.output.with_suffix('.tmp');temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');temp.replace(args.output)
    for k,v in sorted(result['metrics'].items()):print(f'{k}: {v["value"]} ({v["date"]}, {v["status"]})')
    if result['errors']:print('Retained/missing sources: '+json.dumps(result['errors'],ensure_ascii=False),file=sys.stderr)
    if args.strict and result['errors']:return 1
    if not any(m.get('status')=='ok' for m in result['metrics'].values()):return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
