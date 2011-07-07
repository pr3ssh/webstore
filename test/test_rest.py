import shutil
import json
from StringIO import StringIO
from csv import DictReader
import webstore.web as ws
import unittest
import tempfile

JSON = 'application/json'
CSV = 'text/csv'

CSV_FIXTURE = """date,temperature,place
2011-01-01,1,Galway
2011-01-02,-1,Galway
2011-01-03,0,Galway
2011-01-01,6,Berkeley
2011-01-02,8,Berkeley
2011-01-03,5,Berkeley"""

JSON_FIXTURE = [{'row1': 'rowvalue1', 'foo': 'bar'},
                {'row1': 'value2', 'foo': 'schnasel'}]

class WebstoreTestCase(unittest.TestCase):

    def setUp(self):
        ws.app.config['SQLITE_DIR'] = tempfile.mkdtemp()
        ws.app.config['TESTING'] = True
        self.app = ws.app.test_client()
        self.make_fixtures()

    def tearDown(self):
        shutil.rmtree(ws.app.config['SQLITE_DIR'])

    def make_fixtures(self):
        self.app.post('/db/fixtures?table=json',
                content_type=JSON,
                data=json.dumps(JSON_FIXTURE))
        self.app.post('/db/fixtures?table=csv',
                content_type=CSV,
                data=CSV_FIXTURE)

    def test_no_tables(self):
        response = self.app.get('/db/no_tables', headers={'Accept': JSON})
        assert response.data == json.dumps([])

    def test_create_json_table(self):
        response = self.app.post('/db/create_json_table?table=foo',
                headers={'Accept': JSON}, content_type=JSON,
                data=json.dumps(JSON_FIXTURE))
        body = json.loads(response.data)
        assert 'Successfully' in body['message'], body
        assert 'success' == body['state'], body
        assert '/db/create_json_table/foo' == body['url'], body

    def test_create_csv_table(self):
        response = self.app.post('/db/create_csv_table?table=foo',
                headers={'Accept': CSV}, content_type=CSV,
                data=CSV_FIXTURE)
        assert 'message,state,url' in response.data, response.data
        assert 'Successfully' in response.data, response.data
        assert '/db/create_csv_table/foo' in response.data, response.data

    def test_index_with_tables(self):
        response = self.app.get('/db/fixtures', headers={'Accept': JSON})
        data = json.loads(response.data)
        assert len(data) == 2, data

    def test_cannot_overwrite_table(self):
        response = self.app.post('/db/fixtures/json',
                headers={'Accept': JSON}, content_type=JSON,
                data=json.dumps(JSON_FIXTURE))
        body = json.loads(response.data)
        assert response.status == "409 CONFLICT", response.status
        assert body['state'] == 'error', body

    def test_does_not_exist(self):
        response = self.app.get('/db/fixtures/not_there')
        assert response.status.startswith("404"), response.status

    def test_read_json_representation(self):
        response = self.app.get('/db/fixtures/json',
            headers={'Accept': JSON})
        body = json.loads(response.data)
        assert len(body) == len(JSON_FIXTURE), body
    
    def test_read_json_representation_with_limit_and_offset(self):
        response = self.app.get('/db/fixtures/csv?_limit=2&_offset=2',
            headers={'Accept': JSON})
        body = json.loads(response.data)
        assert body[0].get('place')=='Galway', body
        assert body[1].get('place')=='Berkeley', body

    def test_read_csv_representation(self):
        response = self.app.get('/db/fixtures/csv',
            headers={'Accept': CSV})
        reader = DictReader(StringIO(response.data))
        flds = ['__id__', 'date', 'place', 'temperature']
        assert reader.fieldnames == flds, reader.fieldnames
        assert len(list(reader))==6
    
    def test_read_json_representation_invalid_limit(self):
        response = self.app.get('/db/fixtures/csv?_limit=BANANA',
            headers={'Accept': JSON})
        body = json.loads(response.data)
        assert response.status.startswith("400"), response.status
        assert 'BANANA' in body.get('message'), body
    
    def test_read_json_representation_invalid_sort(self):
        response = self.app.get('/db/fixtures/csv?_sort=theotherway',
            headers={'Accept': JSON})
        body = json.loads(response.data)
        assert response.status.startswith("400"), response.status
        assert 'Invalid sorting format' in body.get('message'), body
    
    def test_read_json_representation_sort(self):
        response = self.app.get('/db/fixtures/csv?_sort=desc:temperature',
            headers={'Accept': JSON})
        body = json.loads(response.data)
        assert body[0]['temperature'] == '8', body
        assert body[0]['place'] == 'Berkeley', body

    def test_put_additional_row(self):
        update = [{'place': 'Honolulu', 'climate': 'mild'}]
        response = self.app.put('/db/fixtures/csv',
                headers={'Accept': JSON}, content_type=JSON,
                data=json.dumps(update))
        assert response.status.startswith("201"), response.status
        response = self.app.get('/db/fixtures/csv?climate=mild',
            headers={'Accept': JSON})
        body = json.loads(response.data)
        assert body[0]['place'] == 'Honolulu', body
    
    def test_put_additional_row_as_json_dict(self):
        update = {'place': 'Honolulu', 'climate': 'mild'}
        response = self.app.put('/db/fixtures/csv',
                headers={'Accept': JSON}, content_type=JSON,
                data=json.dumps(update))
        assert response.status.startswith("201"), response.status
        response = self.app.get('/db/fixtures/csv?climate=mild',
            headers={'Accept': JSON})
        body = json.loads(response.data)
        assert body[0]['place'] == 'Honolulu', body

    def test_put_additional_row_with_unique_selector(self):
        update = [{'place': 'Berkeley', 'country': 'United States'}]
        response = self.app.put('/db/fixtures/csv?unique=place',
                headers={'Accept': JSON}, content_type=JSON,
                data=json.dumps(update))
        assert response.status.startswith("201"), response.status
        response = self.app.get('/db/fixtures/csv?place=Berkeley',
            headers={'Accept': JSON})
        body = json.loads(response.data)
        assert body[0]['country'] == 'United States', body

    def test_put_sql_request(self):
        query = 'SELECT * FROM "csv"'
        response = self.app.put('/db/fixtures',
                headers={'Accept': JSON}, content_type='text/sql',
                data=query)
        body = json.loads(response.data)
        assert len(body) == 6, body
        assert body[0]['place'] is not None, body

if __name__ == '__main__':
    unittest.main()



