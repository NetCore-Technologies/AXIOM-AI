"""Bounded JSONL profiling. Only structural metadata is returned."""
from __future__ import annotations
import hashlib, json
from collections import Counter
from pathlib import Path
from typing import Any
DEFAULT_MAX_BYTES=64*1024*1024
DEFAULT_MAX_ROWS=100_000
DEFAULT_MAX_LINE_BYTES=1024*1024
MAX_TRACKED_FIELDS=500
SENSITIVE=("password","passwd","secret","token","api_key","apikey","access_key","authorization","email","phone","mobile","address","ssn","social_security","credit_card","card_number","date_of_birth","birth_date","cookie")
def _reject_constant(value: str) -> None: raise ValueError(f"Non-standard JSON constant: {value}")
def _type_name(v: Any) -> str:
 if v is None:return "null"
 if isinstance(v,bool):return "boolean"
 if isinstance(v,int):return "integer"
 if isinstance(v,float):return "number"
 if isinstance(v,str):return "string"
 if isinstance(v,list):return "array"
 if isinstance(v,dict):return "object"
 return "unknown"
def _sensitive(name: str) -> bool:
 n=name.casefold().replace("-","_").replace(" ","_")
 return any(p in n for p in SENSITIVE)
def profile_jsonl(path: str|Path, *, max_bytes: int=DEFAULT_MAX_BYTES, max_rows: int=DEFAULT_MAX_ROWS, max_line_bytes: int=DEFAULT_MAX_LINE_BYTES) -> dict[str,Any]:
 if any(type(x) is not int or x<1 for x in (max_bytes,max_rows,max_line_bytes)): raise ValueError("Profiling limits must be positive integers.")
 source=Path(path).expanduser().resolve(strict=True)
 if not source.is_file(): raise ValueError("Dataset path must be a regular file.")
 size=source.stat().st_size; read_bytes=lines=valid=invalid=empty=duplicates=overlong=omitted=0; truncated=False
 seen=set(); counts=Counter(); nulls=Counter(); types={}
 with source.open("rb") as f:
  while lines<max_rows:
   remaining=max_bytes-read_bytes
   if remaining<=0: truncated=True; break
   raw=f.readline(min(max_line_bytes+1,remaining+1))
   if not raw: break
   if len(raw)>remaining: read_bytes+=remaining; truncated=True; break
   read_bytes+=len(raw); lines+=1
   if len(raw)>max_line_bytes:
    invalid+=1; overlong+=1
    while raw and not raw.endswith(b"\n"):
     remaining=max_bytes-read_bytes
     if remaining<=0: truncated=True; break
     raw=f.readline(min(65536,remaining+1))
     if len(raw)>remaining: read_bytes+=remaining; truncated=True; break
     read_bytes+=len(raw)
    if truncated: break
    continue
   raw=raw.strip()
   if not raw: empty+=1; continue
   try: row=json.loads(raw.decode("utf-8"),parse_constant=_reject_constant)
   except (UnicodeDecodeError,json.JSONDecodeError,ValueError): invalid+=1; continue
   if not isinstance(row,dict): invalid+=1; continue
   valid+=1; canonical=json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(",",":"),allow_nan=False)
   fp=hashlib.sha256(canonical.encode("utf-8")).hexdigest()
   if fp in seen: duplicates+=1
   else: seen.add(fp)
   for key,value in row.items():
    name=str(key)
    if name not in counts and len(counts)>=MAX_TRACKED_FIELDS: omitted+=1; continue
    counts[name]+=1
    if value is None:nulls[name]+=1
    types.setdefault(name,Counter())[_type_name(value)]+=1
 if (lines>=max_rows or read_bytes>=max_bytes) and read_bytes<size: truncated=True
 fields=[]
 for name in sorted(counts):
  n=counts[name]; shown=name if len(name)<=160 else name[:159]+"…"
  fields.append({"name":shown,"occurrences":n,"null_count":nulls[name],"null_rate":round(nulls[name]/n,4) if n else 0.0,"types":dict(sorted(types[name].items())),"possibly_sensitive":_sensitive(name)})
 sensitive=[x["name"] for x in fields if x["possibly_sensitive"]]; warnings=[]
 if invalid:warnings.append("Invalid or unsupported rows were detected.")
 if duplicates:warnings.append("Duplicate valid rows were detected.")
 if sensitive:warnings.append("Potentially sensitive field names were detected; review locally.")
 if truncated:warnings.append("Profile is partial because a scanning limit was reached.")
 if omitted:warnings.append("Field tracking limit reached; some fields were omitted.")
 return {"format":"jsonl","file_name":source.name,"file_size_bytes":size,"bytes_scanned":read_bytes,"lines_scanned":lines,"valid_rows":valid,"invalid_rows":invalid,"empty_rows":empty,"duplicate_rows":duplicates,"overlong_rows":overlong,"unique_fields_tracked":len(fields),"omitted_field_occurrences":omitted,"possibly_sensitive_fields":sensitive,"privacy_review_recommended":bool(sensitive),"truncated":truncated,"fields":fields,"warnings":warnings,"limits":{"max_bytes":max_bytes,"max_rows":max_rows,"max_line_bytes":max_line_bytes}}
