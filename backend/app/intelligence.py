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
# Only a narrow vocabulary can leave the machine. Unknown words fail closed.
SAFE_WORDS=set('the a an is are was hai he hain ka ki ke ko se mein main me in at on near lab cse library reading area room 3 4 wifi wi fi net internet network slow down broken not no nahi nahin naheen working chal raha rahi unavailable faulty issue problem connection signal weak intermittent constantly cuts out light power bijli fan pankha ac water pani projector computer pc socket chair other'.split())

def normalize(value): return ' '.join(unicodedata.normalize('NFKC',value or '').lower().split())

def screen(value, visibility):
    text=normalize(value)
    confidential=visibility!='PUBLIC' or bool(CONDUCT.search(text))
    sensitive=confidential or bool(PRIVATE.search(text))
    instruction=bool(INJECTION.search(text))
    hazards=list(HAZARD.finditer(text)); hazard=False; uncertain=False
    for match in hazards:
        preceding=text[max(0,match.start()-35):match.start()]
        preceding=re.split(r'\bbut\b|\blekin\b|[.;]',preceding)[-1]
        if NEGATION.search(preceding): uncertain=True
        else: hazard=True
    tokens=re.findall(r'[a-z0-9]+',text)
    external=bool(tokens) and not sensitive and not instruction and all(t in SAFE_WORDS for t in tokens)
    return {'confidential':confidential,'sensitive':sensitive,'instruction':instruction,'hazard':hazard,'hazard_uncertain':uncertain,'external_safe':external}

def classify_local(text):
    normalized=normalize(text)
    matches={category for alias,category in ALIASES.items() if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',normalized)}
    return next(iter(matches)) if len(matches)==1 else None

def location_match(conn, description, selected_id=None, location_text=None):
    rows=[dict(r) for r in conn.execute(select(s.locations).where(s.locations.c.active.is_(True))).mappings()]
    aliases=[dict(r) for r in conn.execute(select(s.location_aliases)).mappings()]
    selected=next((r for r in rows if r['id']==selected_id),None)
    if selected_id and not selected:return None,'Unknown selected location'
    normalized=normalize(description); match=ROOM.search(normalized)
    query=normalize(location_text) if location_text else (match.group(0) if match else '')
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
    if selected:return selected,None
    # Only exact, unambiguous multi-word names are detected from free text.
    matches=[r for r in rows if len(normalize(r['name']).split())>1 and normalize(r['name']) in normalized]
    if len(matches)==1:return matches[0],None
    return None,'Select or clarify the location'
