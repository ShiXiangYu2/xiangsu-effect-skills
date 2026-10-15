"""Read-only audits, source checks, reviewed candidates, approval-gated installation."""
import argparse,ast,datetime,difflib,hashlib,json,re,subprocess,sys,uuid
from pathlib import Path

def digest(data):return hashlib.sha256(data).hexdigest()
def files(root):
 out={}
 for p in sorted(root.rglob('*')):
  if p.is_symlink():raise ValueError('Symlink package entry rejected: '+str(p))
  if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.tmp'):out[p.relative_to(root).as_posix()]=digest(p.read_bytes())
 return out
def tree(root):return digest(json.dumps(files(root),sort_keys=True,separators=(',',':')).encode())
def move(source,destination):
 helper=Path(__file__).with_name('atomic_move.ps1')
 subprocess.run(['powershell','-NoProfile','-File',str(helper),'-Source',str(source),'-Destination',str(destination)],check=True,capture_output=True)
def write(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.tmp');temp.write_bytes(data);assert temp.read_bytes()==data;move(temp,path)
def jswrite(path,obj):write(path,json.dumps(obj,ensure_ascii=False,indent=2).encode('utf-8'))
def copy(root,out):
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True)
 for rel in files(root):write(out/rel,(root/rel).read_bytes())
 assert tree(root)==tree(out)
def audit(root):
 errors=[]
 try:
  text=(root/'SKILL.md').read_text(encoding='utf-8-sig');m=re.match(r'^---\s*\n(.*?)\n---\s*\n',text,re.S);assert m,'Missing frontmatter'
  front={}
  for line in m[1].splitlines():
   match=re.match(r'^(name|description):\s*(.+)$',line)
   if match:front[match[1]]=match[2].strip().strip(chr(34)+chr(39))
  name=front['name'];assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name) and len(name)<=64;assert front['description']
  manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'));assert manifest['name']==name;assert manifest['version']==(root/'VERSION').read_text().strip();assert manifest['require_human_approval'] is True
  assert manifest['status']=='validated_candidate';assert manifest['recursive_deletion'] is False
  for p in root.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8'),filename=str(p))
  for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',text):
   if '://' not in target and not target.startswith(('#','/')):assert (root/target).is_file(),target
 except Exception as exc:errors.append(str(exc));name=None;manifest={}
 return {'ok':not errors,'errors':errors,'name':name,'version':manifest.get('version'),'sha256':tree(root) if not errors else None,'files':len(files(root))}
def sources(root):
 entries=json.loads((root/'manifest.json').read_text(encoding='utf-8')).get('sources',[]);report=[]
 for entry in entries:
  p=Path(entry['path']) if entry.get('path') else None
  actual=digest(p.read_bytes()) if p and p.is_file() else None
  report.append({**entry,'current_sha256':actual,'status':('unchanged' if actual==entry.get('sha256') else 'changed') if actual else 'unavailable'})
 return {'checks':report,'remote_checks_performed':False,'warning':'No remote auto-upgrade claim; browse official sources when needed.'}
def plan(candidate,roots,out):
 valid=audit(candidate);assert valid['ok'],valid
 entries=[];diff=[];new=files(candidate)
 for root in roots:
  root=root.resolve();assert root.name=='skills';target=root/valid['name'];old=files(target) if target.is_dir() else {}
  entries.append({'target':str(target),'before_sha256':tree(target) if target.is_dir() else None})
  for rel in sorted(set(old)|set(new)):
   if old.get(rel)==new.get(rel):continue
   before=(target/rel).read_text(encoding='utf-8',errors='replace') if rel in old else ''
   after=(candidate/rel).read_text(encoding='utf-8',errors='replace') if rel in new else ''
   diff.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=str(target/rel),tofile=str(candidate/rel)))
 payload={'candidate':str(candidate.resolve()),'audit':valid,'entries':entries,'sources':sources(candidate),'requires_human_consent':True}
 jswrite(out,payload);write(out.with_suffix('.diff'),''.join(diff).encode('utf-8'))
 return {'plan':str(out),'approval_plan_sha256':digest(out.read_bytes()),'candidate_sha256':valid['sha256'],'targets':entries,'audit':valid}
def install(planfile,approval):
 # Technical checksum is NOT human consent. Caller may use this only after the user approves the reviewed plan.
 raw=planfile.read_bytes();expected=digest(raw)
 if approval!=expected:raise PermissionError('Human approval for this exact plan is required; approval checksum mismatch.')
 plan=json.loads(raw);candidate=Path(plan['candidate']);valid=audit(candidate)
 if not valid['ok'] or valid['sha256']!=plan['audit']['sha256']:raise PermissionError('Candidate changed after review; new human approval required.')
 entries=plan['entries'];allowed=[Path.home()/'.codex'/'skills',Path.home()/'.agents'/'skills']
 for entry in entries:
  target=Path(entry['target']).resolve();assert target.parent in [p.resolve() for p in allowed] and target.name==valid['name']
  current=tree(target) if target.is_dir() else None
  if current!=entry['before_sha256']:raise PermissionError('Installed version changed after review; regenerate plan.')
 stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
 staged=[];activated=[]
 for entry in entries:
  target=Path(entry['target']);stage=target.parent.parent/'.skill-staging'/(target.name+'-'+stamp);copy(candidate,stage);assert audit(stage)['sha256']==valid['sha256'];staged.append((target,stage))
 try:
  for target,stage in staged:
   target.parent.mkdir(parents=True,exist_ok=True);backup=None
   if target.exists():backup=target.parent.parent/'.skill-backups'/(target.name+'-'+stamp);backup.parent.mkdir(parents=True,exist_ok=True);move(target,backup)
   activated.append((target,backup));move(stage,target)
   assert audit(target)['sha256']==valid['sha256']
 except Exception:
  for target,backup in reversed(activated):
   if target.exists():failed=target.parent.parent/'.skill-staging'/(target.name+'-failed-'+stamp);move(target,failed)
   if backup and backup.exists():move(backup,target)
  raise
 return {'ok':True,'installed':[{'path':str(t),'backup':str(b) if b else None} for t,b in activated],'sha256':valid['sha256']}
def prepare(current,output,feedback,source):
 assert audit(current)['ok'];copy(source or current,output)
 m=json.loads((output/'manifest.json').read_text(encoding='utf-8'));version=[int(x) for x in m['version'].split('.')];version[-1]+=1;m['version']='.'.join(map(str,version));m['status']='draft'
 jswrite(output/'manifest.json',m);write(output/'VERSION',(m['version']+'\n').encode())
 write(output/'references'/'optimization-evidence.md',('# Optimization evidence\n\n'+feedback.read_text(encoding='utf-8')+'\n\nAgent must make evidence-backed changes, test behavior, and set validated_candidate before planning.\n').encode('utf-8'))
 return {'candidate':str(output),'status':'draft','installed_unchanged':True}
def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['audit','check-sources','plan','install','prepare']);p.add_argument('--skill',type=Path);p.add_argument('--target-root',type=Path,nargs='+');p.add_argument('--out',type=Path);p.add_argument('--plan',type=Path);p.add_argument('--approval');p.add_argument('--feedback',type=Path);p.add_argument('--source',type=Path);a=p.parse_args()
 if a.command=='audit':result=audit(a.skill);code=0 if result['ok'] else 1
 elif a.command=='check-sources':result=sources(a.skill);code=0
 elif a.command=='plan':result=plan(a.skill,a.target_root,a.out);code=0
 elif a.command=='install':result=install(a.plan,a.approval);code=0
 else:result=prepare(a.skill,a.out,a.feedback,a.source);code=0
 print(json.dumps(result,ensure_ascii=False,indent=2));return code
if __name__=='__main__':
 try:raise SystemExit(main())
 except Exception as exc:print('ERROR:',str(exc),file=sys.stderr);raise SystemExit(2)
