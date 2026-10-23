import datetime as dt
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import update_data as u
from check_data import validate

class DataTests(unittest.TestCase):
    def test_fred_missing_values_duplicates_and_zero(self):
        text='DATE VALUE\n2025-01-01 0\n2025-01-02 .\n2025-01-03 2\n2025-01-04 -1\n2025-01-05 3\n2025-01-06 4\n2025-01-06 5'
        rows=u.fred_rows(text)
        self.assertEqual(len(rows),5)
        self.assertEqual(rows[0]['value'],0)
        self.assertEqual(rows[-1]['value'],5)
    def test_fred_html_table_only(self):
        text='<html><script>2025-02-01 99999</script><pre>'+''.join(f'#2025-01-0{i}|{i}\n' for i in range(1,7))+'</pre></html>'
        rows=u.fred_rows(text)
        self.assertEqual(len(rows),6)
        self.assertEqual(rows[-1],{'date':'2025-01-06','value':6})
    def test_html_error_is_not_data(self):
        with self.assertRaises(ValueError):u.fred_rows('<html>Temporarily unavailable 2025-01-01 503</html>')
    def test_mof_column_and_era(self):
        raw='国債金利情報\r\n基準日,1年,10年,30年\r\nR7.12.30,1,2.9,3.5\r\nR8.1.5,1.1,3.0,3.6'.encode('cp932')
        with patch.object(u,'fetch',return_value=(raw,None)):
            data=u.japan_yield()
        self.assertEqual(data['date'],'2026-01-05');self.assertEqual(data['value'],3)
    def test_cpi_definition_and_month(self):
        text='全国2026年(令和8年)9月分(2026年10月23日公表) ポイント 総合 前年同月比は2.1%の上昇 生鮮食品を除く 前年同月比は2.0%の上昇 生鮮食品及びエネルギー除く 前年同月比は0.2%の下落'
        t=u.Text();t.feed(text)
        with patch.object(u,'document',return_value=(t,'')):
            result=u.japan_cpi()
        self.assertEqual(result['jp_cpi']['value'],2.1);self.assertEqual(result['jp_core']['value'],2.0);self.assertEqual(result['jp_core_energy']['value'],-.2)
    def test_retention_and_policy_pair(self):
        prev={'metrics':{k:u.metric(2,'2025-01-01','https://example.org','%') for k in ['fx','jp_cpi','us_policy_low','us_policy_high']}}
        with patch.object(u,'fred',side_effect=ValueError('offline')),patch.object(u,'japan_yield',side_effect=ValueError('offline')),patch.object(u,'japan_cpi',side_effect=ValueError('offline')),patch.object(u,'us_cpi',side_effect=ValueError('offline')),patch.object(u,'boj_policy',side_effect=ValueError('offline')):
            result=u.collect(prev)
        self.assertEqual(result['metrics']['fx']['value'],2);self.assertEqual(result['metrics']['fx']['date'],'2025-01-01');self.assertEqual(result['metrics']['fx']['status'],'retained');self.assertEqual(prev['metrics']['fx']['status'],'ok');self.assertEqual(len(result['errors']),10)
    def test_rejects_future_and_nonfinite(self):
        tomorrow=(dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=3)).isoformat()
        with self.assertRaises(ValueError):u.metric(2,tomorrow,'https://example.org','%')
        with self.assertRaises(ValueError):u.metric(float('nan'),'2025-01-01','https://example.org','%')
    def test_live_payload(self):
        import json
        data=json.loads((Path(__file__).resolve().parents[1]/'data/latest.json').read_text())
        self.assertTrue(validate(data));self.assertEqual(data['schema_version'],1)

if __name__=='__main__':unittest.main()
