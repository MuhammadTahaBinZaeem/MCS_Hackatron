import io
from PIL import Image
from test_stage02 import prepared,ORIGIN
from test_stage03 import student_client

def test_private_upload_and_type_validation(prepared):
    client,path=prepared('demo',True)
    with client:
        student_client(client,path)
        image=io.BytesIO();Image.new('RGB',(8,8),'white').save(image,format='PNG')
        declarations={'purpose':'SUPPORTING_EVIDENCE','faces':'YES','nsfw':'NO','sensitive':'NO','public_requested':'true','external_consent':'false'}
        result=client.post('/api/v1/attachments',headers=ORIGIN,files={'file':('sample.png',image.getvalue(),'image/png')},data=declarations)
        assert result.status_code==200
        attachment=result.json()['id']
        assert result.json()['face_detection']=='NOT_CONFIGURED'
        assert client.get('/api/v1/attachments/'+attachment).status_code==200
        bad=client.post('/api/v1/attachments',headers=ORIGIN,files={'file':('sample.png',b'not a png','image/png')},data=declarations)
        assert bad.status_code in {400,415}
        report=client.post('/api/v1/reports',headers={**ORIGIN,'Idempotency-Key':'file-test'},json={'text':'wifi not working lab 4','attachment_ids':[attachment]})
        assert report.status_code==200
