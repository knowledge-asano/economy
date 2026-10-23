"""Reject invalid published data rather than serving an invented 'latest' value."""
import datetime as dt
import json, math
from pathlib import Path

def validate(data):
    if data.get('schema_version')!=1:raise ValueError('Unknown schema')
    if not isinstance(data.get('metrics'),dict) or not data['metrics']:raise ValueError('No observations')
    for key,m in data['metrics'].items():
        if not isinstance(m.get('value'),(int,float)) or not math.isfinite(m['value']):raise ValueError(f'{key}: invalid value')
        if dt.date.fromisoformat(m['date'])>dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=1):raise ValueError(f'{key}: future date')
        if not m.get('source','').startswith('https://'):raise ValueError(f'{key}: source missing')
        if m.get('status') not in ('ok','retained'):raise ValueError(f'{key}: invalid status')
        for row in m.get('history',[]):
            dt.date.fromisoformat(row['date'])
            if not math.isfinite(row['value']):raise ValueError(f'{key}: invalid chart value')
    return True

if __name__=='__main__':
    validate(json.loads((Path(__file__).resolve().parents[1]/'data/latest.json').read_text()))
    print('Dated data, values and sources validated.')
