"""Small, explicit optional review requests. No unchecked instructions are added."""
OPTIONS={
    'evidence':('원문 근거','판단 근거인 영어 구절을 짧게 인용하고 페이지를 표시하세요.'),
    'accuracy':('번역 정확성','기존 번역에 누락·첨가·의미 변형이 있는지 확인하세요.'),
    'alternative':('대안 번역','의미를 유지한 자연스러운 한국어 번역을 1개 제시하세요.'),
    'terminology':('용어·약어','용어·약어의 문맥상 뜻을 설명하고 필요하면 일반적인 뜻과 구분하세요.'),
    'structure':('문장 구조','수식 관계와 대명사·지시어가 가리키는 대상을 설명하세요.'),
    'strength':('뉘앙스·주장 강도','가능성·확실성·조건과 상관·인과의 강도가 어떻게 표현되는지 비교하세요.'),
    'uncertainty':('불확실성','복수 해석·근거 부족·자동 문장 연결 오류 중 관련된 한계를 짧게 밝히세요.')
}
HEADING='사용자가 선택한 추가 검토(쉼표로 구분한 복수 선택): '
GUIDE='핵심 답을 먼저 제시하고 선택한 항목만 추가하세요. 겹치는 설명은 합쳐 간결하게 쓰세요.'

def catalog():
    return dict(items=[dict(id=key,label=value[0],instruction=value[1]) for key,value in OPTIONS.items()],heading=HEADING,guide=GUIDE)

def normalize(values=None):
    if values is None:return []
    if isinstance(values,str):values=[v.strip() for v in values.split(',') if v.strip()]
    if not isinstance(values,list) or len(values)>32:raise ValueError('추가 검토 항목을 확인하세요.')
    names={v[0]:key for key,v in OPTIONS.items()};selected=set()
    for value in values:
        if not isinstance(value,str):raise ValueError('추가 검토 항목을 확인하세요.')
        key=value if value in OPTIONS else names.get(value)
        if key is None:raise ValueError('알 수 없는 추가 검토 항목입니다.')
        selected.add(key)
    return [key for key in OPTIONS if key in selected]

def labels(values=None):return [OPTIONS[key][0] for key in normalize(values)]

def prompt_suffix(values=None):
    selected=normalize(values)
    if not selected:return ''
    return '\n\n'+HEADING+', '.join(labels(selected))+'\n'+GUIDE+'\n'+\
        '\n'.join(OPTIONS[key][0]+': '+OPTIONS[key][1] for key in selected)
