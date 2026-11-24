"""Privacy-first Stage 03 classification. Never writes public issues."""
import re
import unicodedata
from rapidfuzz import fuzz
from sqlalchemy import select
from app import schema as s

ALIASES={'wifi':'NETWORK','wi fi':'NETWORK','internet':'NETWORK','network':'NETWORK','net':'NETWORK',
         'computer':'COMPUTING','pc':'COMPUTING','laptop':'COMPUTING',
         'bijli':'ELECTRICAL','light':'ELECTRICAL','socket':'ELECTRICAL','pankha':'ELECTRICAL','power':'ELECTRICAL',
         'ac':'FACILITIES','pani':'FACILITIES','water':'FACILITIES','chair':'FACILITIES','toilet':'FACILITIES',
         'projector':'ACADEMIC','whiteboard':'ACADEMIC','food':'CAFETERIA','cafeteria':'CAFETERIA'}
CONDUCT=re.compile(r'\b(harass\w*|ragging|ragged|bully\w*|assault\w*|sexual|stalk\w*|threat\w*|tang\s+kar\w*|pareshan|abuse\w*)\b',re.I)
PRIVATE=re.compile(r'\b(student\s+(?:id|number)|phone|email|address|identity|name|medical\s+record|confidential|private|personal|suicid\w*|rape\w*)\b|[\w.+-]+@[\w.-]+|\b\d{7,}\b',re.I)
INJECTION=re.compile(r'\b(ignore|system prompt|developer|instructions|mark (?:this|it)|pretend|override|you are)\b',re.I)
HAZARD=re.compile(r'\b(fire|aag|sparks?|chingari|gas\s*(?:leak|leaking)|smoke|dhuan|behosh|unconscious|medical\s+emergency|heart\s+attack|electrocut\w*|collapse\w*)\b',re.I)
NEGATION=re.compile(r"\b(no|not|without|never|isn't|isnt|nahi|nahin|naheen|agar|if|hypothetical)\b",re.I)
ROOM=re.compile(r'\b(?:(?:cse\s+)?lab|room)\s*[-#]?\s*(\d+)\b',re.I)
# Only these locally derived concepts can be sent externally; unknown words are
# omitted, not treated as evidence of a private or publishable report.
SAFE_CONCEPTS=set('lab cse ee is library cafeteria reading area room wifi network internet net slow down broken not no nahi nahin naheen working chal raha rahi unavailable faulty problem connection signal weak intermittent cuts light power bijli fan pankha ac water pani projector computer pc socket chair'.split())
UNCERTAIN=re.compile(r'\b(i|me|my|myself|he|she|they|someone|person|teacher|student|staff|admin|professor|mera|meri|mujhe|usne|kisi|larka|larki)\b',re.I)
PERSON_NAME=re.compile(r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}\b')

def normalize(value): return ' '.join(unicodedata.normalize('NFKC',value or '').lower().split())

def screen(value, visibility):
    text=normalize(value)
    confidential=visibility!='PUBLIC' or bool(CONDUCT.search(text))
    name_text=re.sub(r'\b(?:Library Reading Area|CSE Lab|Lab)\b','',value or '',flags=re.I)
    sensitive=confidential or bool(PRIVATE.search(text)) or bool(UNCERTAIN.search(text)) or bool(PERSON_NAME.search(name_text))
    instruction=bool(INJECTION.search(text))
    hazards=list(HAZARD.finditer(text)); hazard=False; uncertain=False
    for match in hazards:
        preceding=text[max(0,match.start()-35):match.start()]
        preceding=re.split(r'\bbut\b|\blekin\b|[.;]',preceding)[-1]
        if NEGATION.search(preceding): uncertain=True
        else: hazard=True
    tokens=re.findall(r'[a-z0-9]+',text)
    external=bool(tokens) and not sensitive and not instruction
    return {'confidential':confidential,'conduct':bool(CONDUCT.search(text)),'sensitive':sensitive,'instruction':instruction,'hazard':hazard,'hazard_uncertain':uncertain,'external_safe':external}

def external_summary(value):
    """Only allow-listed concepts and explicit room/asset numbers leave the host."""
    tokens=re.findall(r'[a-z0-9]+',normalize(value));clean=[]
    for i,token in enumerate(tokens):
        if token in SAFE_CONCEPTS or (token.isdigit() and i and tokens[i-1] in {'lab','room','pc'}):clean.append(token)
    return ' '.join(clean)

def local_details(value):
    text=normalize(value)
    asset=re.search(r'\b(pc|computer|projector|socket)\s*[-#]?\s*(\d+)\b',text)
    failure='UNAVAILABLE' if re.search(r'\b(unavailable|not working|not (?:working|running)|nahi chal|nahin chal|down|broken|band)\b',text) else 'SLOW' if re.search(r'\b(slow|weak|dheema|ahista)\b',text) else None
    impact='COMPLETE_DISRUPTION' if failure=='UNAVAILABLE' else 'PARTIAL_DISRUPTION' if failure=='SLOW' else 'UNKNOWN'
    subtype=next((code for pattern,code in [(r'\b(wifi|wi fi|net)\b','WIFI'),(r'\binternet\b','INTERNET'),(r'\blan\b','LAN'),(r'\bprojector\b','PROJECTOR'),(r'\b(harassment|harass\w*|tang\s+kar\w*)\b','HARASSMENT'),(r'\b(ragging|ragged)\b','RAGGING')] if re.search(pattern,text)),None)
    return {'subcategory':subtype,'failure_type':failure,'asset_identifier':f'{asset.group(1).upper()} {asset.group(2)}' if asset else None,'impact':impact}

def confidential_details(value):
    text=normalize(value); details=[]
    if re.search(r'\b(ragging|ragged)\b',text):details.append('Ragging reported')
    if re.search(r'\b(harass\w*|tang\s+kar\w*|pareshan)\b',text):details.append('Harassment reported')
    if re.search(r'\b(threat\w*|dhamki)\b',text):details.append('Threats reported')
    if re.search(r'\b(bully\w*|bullying)\b',text):details.append('Bullying reported')
    if re.search(r'\b(repeated\w*|daily|bar bar|roz)\b',text):details.append('Repeated incidents reported')
    if re.search(r'\b(physical|hit|hitting|pushed|maar\w*)\b',text):details.append('Physical conduct reported')
    if re.search(r'\b(verbal|verbally|words|gaali)\b',text):details.append('Verbal conduct reported')
    return '; '.join(details) if details else 'Details require confidential follow-up'

def classify_local(text):
    normalized=normalize(text)
    matches={category for alias,category in ALIASES.items() if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',normalized)}
    return next(iter(matches)) if len(matches)==1 else None

def location_match(conn, description, selected_id=None, location_text=None, candidate=None):
    rows=[dict(r) for r in conn.execute(select(s.locations).where(s.locations.c.active.is_(True))).mappings()]
    aliases=[dict(r) for r in conn.execute(select(s.location_aliases)).mappings()]
    selected=next((r for r in rows if r['id']==selected_id),None)
    if selected_id and not selected:return None,'Unknown selected location'
    normalized=normalize(description); match=ROOM.search(normalized)
    query=normalize(location_text) if location_text else (match.group(0) if match else '')
    mentioned=set(ROOM.findall(normalized))
    if len(mentioned)>1:return None,'Multiple locations require clarification'
    if location_text and mentioned and set(re.findall(r'\d+',normalize(location_text))) != mentioned:return None,'Selected location conflicts with report'
    if not query and candidate:
        proposed=normalize(candidate)
        # AI candidates must occur in the original text; they never supply facts.
        if proposed and re.search(r'(?<!\w)'+re.escape(proposed)+r'(?!\w)',normalized):query=proposed
    if query:
        numbers=re.findall(r'\d+',query); scores=[]
        for row in rows:
            names=[normalize(row['name'])]+[a['normalized_alias'] for a in aliases if a['location_id']==row['id']]
            options=[name for name in names if re.findall(r'\d+',name)==numbers]
            score=max((fuzz.ratio(query,name) for name in options),default=0)
            if score>=75:scores.append((score,row))
        scores.sort(key=lambda x:(-x[0],x[1]['id']))
        if not scores:return None,'Unknown location; select a registered location'
        if scores[0][0]<90 or (len(scores)>1 and scores[0][0]-scores[1][0]<10):
            if selected and any(row['id']==selected['id'] and score>=90 for score,row in scores): return selected,None
            return None,'Ambiguous location; confirm the registered location'
        found=scores[0][1]
        if selected and selected['id']!=found['id']:return None,'Selected location conflicts with report'
        return found,None
    names=[]
    for row in rows:
        for name in [normalize(row['name'])]+[a['normalized_alias'] for a in aliases if a['location_id']==row['id']]:
            if len(name)<=2 and not re.search(r'(?<!\w)'+re.escape(row['name'])+r'(?!\w)',description): continue
            if re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',normalized):names.append((len(name),row))
    if names:
        best=max(x[0] for x in names);matches={r['id']:r for length,r in names if length==best}
        if len(matches)>1:return None,'Ambiguous location; confirm the registered location'
        found=next(iter(matches.values()))
        if selected and selected['id']!=found['id']:return None,'Selected location conflicts with report'
        return found,None
    if selected:return selected,None
    words=re.findall(r'[a-z0-9]+',normalized);scores=[]
    for row in rows:
        options=[normalize(row['name'])]+[a['normalized_alias'] for a in aliases if a['location_id']==row['id']]
        best=0
        for name in options:
            count=len(name.split())
            if len(name)<4 or re.search(r'\d',name):continue
            for index in range(len(words)-count+1):
                best=max(best,fuzz.ratio(' '.join(words[index:index+count]),name))
        if best>=75:scores.append((best,row))
    scores.sort(key=lambda pair:(-pair[0],pair[1]['id']))
    if scores and scores[0][0]>=90 and (len(scores)==1 or scores[0][0]-scores[1][0]>=10):return scores[0][1],None
    if scores:return None,'Location needs confirmation'
    return None,'Select or clarify the location'
