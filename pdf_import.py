"""Bounded, local multipart upload decoding. Uploaded names never become paths."""
from email.parser import BytesParser
from email import policy

MAX_UPLOAD=100*1024*1024

def decode_upload(content_type,body,required_pair=True):
    if len(body)>MAX_UPLOAD:raise ValueError('두 PDF의 합계가 100MB 이하여야 합니다.')
    if '\r' in content_type or '\n' in content_type:raise ValueError('파일 전송 형식을 확인하세요.')
    message=BytesParser(policy=policy.default).parsebytes(('Content-Type: '+content_type+'\r\nMIME-Version: 1.0\r\n\r\n').encode('ascii')+body)
    if message.get_content_type()!='multipart/form-data' or not message.is_multipart() or message.defects:raise ValueError('PDF 파일을 선택해 다시 등록하세요.')
    files={};title='';parts=list(message.iter_parts())
    if len(parts)>3:raise ValueError('원문·번역 PDF 한 쌍을 선택하세요.')
    for part in parts:
        if part.is_multipart() or part.defects:raise ValueError('파일 전송 형식을 확인하세요.')
        name=part.get_param('name',header='content-disposition')
        value=part.get_payload(decode=True) or b''
        if name=='title':
            if len(value)>1000:raise ValueError('제목은 200자 이내로 입력하세요.')
            title=value.decode('utf8').strip()
            if len(title)>200:raise ValueError('제목은 200자 이내로 입력하세요.')
        elif name in ('source','translation'):
            filename=(part.get_filename() or '').replace('\\','/').rsplit('/',1)[-1]
            if not required_pair and not filename and not value:continue
            if name in files or not filename.lower().endswith('.pdf') or not value:raise ValueError('원문 PDF와 번역 PDF를 각각 하나씩 선택하세요.')
            files[name]=(filename,value)
        else:raise ValueError('원문·번역 PDF 한 쌍을 선택하세요.')
    if required_pair and set(files)!= {'source','translation'}:raise ValueError('원문 PDF와 번역 PDF를 모두 선택하세요.')
    return files,title
