@component()
export class ShaveDirector extends APJS.BasicScriptComponent {
 @serializeProperty titleObj: APJS.SceneObject;
 @serializeProperty hintObj: APJS.SceneObject;
 @serializeProperty yesObj: APJS.SceneObject;
 @serializeProperty noObj: APJS.SceneObject;
 @serializeProperty clipObj: APJS.SceneObject;
 @serializeProperty hairTpl: APJS.SceneObject;
 @serializeProperty soundObj: APJS.SceneObject;
 @serializeProperty previewState: number = -1;
 private ready: boolean = false;
 private state: number = 0;
 private elapsed: number = 0;
 private lastPreview: number = -1;
 private hasFace: boolean = false;
 private paused: boolean = false;
 private cx: number = 0.5;
 private cy: number = 0.64;
 private hw: number = 0.5;
 private hh: number = 0.5;
 private mat: APJS.Material;
 private title: APJS.Text;
 private hint: APJS.Text;
 private yes: APJS.Text;
 private no: APJS.Text;
 private ys: APJS.ScreenTransform;
 private ns: APJS.ScreenTransform;
 private cs: APJS.ScreenTransform;
 private sound: APJS.AudioComponent;
 private yp: APJS.Vector2f;
 private np: APJS.Vector2f;
 private pool: APJS.SceneObject[] = [];
 private transforms: APJS.ScreenTransform[] = [];
 private ages: number[] = [];
 private velocities: number[] = [];
 private next: number = 0;
 private spawnTime: number = 0;
 private lastLane: number = -1;
 private touch = (event: APJS.IEvent): void => {
  if (!this.ready) return;
  const d = event.args[0] as APJS.TouchData;
  if (d.phase !== APJS.TouchPhase.Began || this.state === 1) return;
  const x = (d.position.x - 0.5)*720;
  const y = (0.5-d.position.y)*1280;
  if (this.hit(this.ys,x,y)) {
   if (this.state === 2) this.change(0);
   else if (this.hasFace) this.change(1);
   else this.hint.text = "请先把脸放进画面";
  } else if (this.state !== 2 && this.hit(this.ns,x,y)) {
   this.change(this.state === 3 ? 0 : 3);
  }
 };
 private record = (_event: APJS.IEvent): void => { if (this.ready) this.change(0); };
 onStart(): void {
  APJS.EventManager.getGlobalEmitter().on(APJS.EventType.Touch,this.touch,this);
  APJS.EventManager.getGlobalEmitter().on(APJS.EventType.RecordStart,this.record,this);
 }
 onDestroy(): void {
  APJS.EventManager.getGlobalEmitter().off(APJS.EventType.Touch,this.touch,this);
  APJS.EventManager.getGlobalEmitter().off(APJS.EventType.RecordStart,this.record,this);
 }
 private hit(st: APJS.ScreenTransform,x: number,y: number): boolean {
  const p=st.anchoredPosition; const s=st.sizeDelta;
  return Math.abs(x-p.x)<Math.max(s.x,230)*0.5 && Math.abs(y-p.y)<Math.max(s.y,80)*0.5;
 }
 private init(): void {
  if (!this.titleObj || !this.hintObj || !this.yesObj || !this.noObj || !this.clipObj || !this.hairTpl || !this.soundObj) return;
  const pp=this.getSceneObject().getComponent("PostProcess") as APJS.PostProcess;
  if (!pp || !pp.custom || !pp.custom.material) return;
  this.mat=pp.custom.material;
  this.title=this.titleObj.getComponent("Text") as APJS.Text;
  this.hint=this.hintObj.getComponent("Text") as APJS.Text;
  this.yes=this.yesObj.getComponent("Text") as APJS.Text;
  this.no=this.noObj.getComponent("Text") as APJS.Text;
  this.ys=this.yesObj.getComponent("ScreenTransform") as APJS.ScreenTransform;
  this.ns=this.noObj.getComponent("ScreenTransform") as APJS.ScreenTransform;
  this.cs=this.clipObj.getComponent("ScreenTransform") as APJS.ScreenTransform;
  this.sound=this.soundObj.getComponent("AudioComponent") as APJS.AudioComponent;
  if (!this.title || !this.hint || !this.yes || !this.no || !this.ys || !this.ns || !this.cs || !this.sound) return;
  this.yp=this.ys.anchoredPosition.clone(); this.np=this.ns.anchoredPosition.clone();
  for(let i=0;i<10;i++){
   const obj=this.hairTpl.clone();
   obj.setEnabledInHierarchy(false);
   this.pool.push(obj);
   this.transforms.push(obj.getComponent("ScreenTransform") as APJS.ScreenTransform);
   this.ages.push(-1);this.velocities.push(0);
  }
  this.ready=true;this.change(0);
  console.log("[Shave] ready pool=10");
 }
 private change(s: number): void {
  this.state=s;this.elapsed=0;this.paused=false;this.lastLane=-1;
  this.sound.stop();this.spawnTime=0;
  for(let i=0;i<this.pool.length;i++){this.pool[i].setEnabledInHierarchy(false);this.ages[i]=-1;}
  this.yesObj.setEnabledInHierarchy(s!==1);
  this.noObj.setEnabledInHierarchy(s!==1 && s!==2);
  this.clipObj.setEnabledInHierarchy(s!==2);
  this.ys.anchoredPosition=s===2 ? new APJS.Vector2f(0,this.yp.y) : this.yp.clone();
  this.ns.anchoredPosition=this.np.clone();
  this.mat.setFloat("_Progress",s===2?1:0);
  if(s===0){this.title.text="是否剃光头？";this.hint.text="点「是」，给头顶放个假";this.yes.text="是，剃光！";this.no.text="再想想";}
  if(s===1){this.title.text="开工！嗡嗡嗡…";this.hint.text="请保持正脸 · 正在剃发";this.sound.play();}
  if(s===2){this.title.text="清爽了！";this.hint.text="今日份烦恼，剃光光";this.yes.text="重新长回来";}
  if(s===3){this.title.text="头发先保住了";this.hint.text="想试试？随时可以反悔";this.yes.text="还是剃吧";this.no.text="重新选择";}
  console.log("[Shave] state="+s);
 }
 onUpdate(dt: number): void {
  if(!this.ready){this.init();return;}
  const result=APJS.AlgorithmManager.getResult();
  this.hasFace=result.getFaceCount()>0;
  if(this.hasFace){
   const r=result.getFaceBaseInfo(0).rect;
   this.cx=r.x+r.width*0.5;this.cy=r.y+r.height*0.8;
   this.hw=Math.max(0.25,r.width*1.65);this.hh=Math.max(0.3,r.height*1.6);
  }
  this.mat.setVector("_Head",new APJS.Vector4f(this.cx,this.cy,this.hw,this.hh));
  if(this.previewState!==this.lastPreview){
   this.lastPreview=this.previewState;
   if(this.previewState>=0 && this.previewState<=3){
    this.change(this.previewState);
    if(this.previewState===1)this.elapsed=2;
   }
  }
  if(this.state===1){
   if(!this.hasFace){
    if(!this.paused){this.sound.pause();this.paused=true;console.log("[Shave] face lost: paused");}
    this.clipObj.setEnabledInHierarchy(false);
    this.hint.text="把脸放回画面，继续理发";
    return;
   }
   if(this.paused){this.sound.resume();this.paused=false;console.log("[Shave] face restored: resumed");}
   this.clipObj.setEnabledInHierarchy(true);
   this.elapsed+=Math.min(dt,0.3);
   const p=Math.min(1,this.elapsed/4);
   this.mat.setFloat("_Progress",p);
   const lane=Math.min(2,Math.floor(p*3));
   const phase=Math.min(1,p*3-lane);
   const top=Math.min(1.05,this.cy+this.hh*0.60);
   const bottom=Math.max(0,this.cy-this.hh*0.90);
   const u=this.cx-this.hw*0.5+this.hw*(lane+0.5)/3;
   const v=top+(bottom-top)*phase;
   const bx=(u-0.5)*720; const by=(v-0.5)*1280;
   this.cs.rotation=180+Math.sin(this.elapsed*70)*2;
   this.cs.anchoredPosition=new APJS.Vector2f(bx,by+this.cs.sizeDelta.y*0.4);
   this.hint.text="请保持正脸 · "+Math.floor(p*100)+"%";
   if(lane!==this.lastLane){this.lastLane=lane;console.log("[Shave] lane="+lane);}
   this.spawnTime+=dt;
   if(this.spawnTime>0.12){
    this.spawnTime=0;const i=this.next;this.next=(i+1)%this.pool.length;
    this.ages[i]=0;this.velocities[i]=(Math.random()-0.5)*260;
    this.transforms[i].anchoredPosition=new APJS.Vector2f(bx,by);
    this.transforms[i].rotation=Math.random()*180;
    this.pool[i].setEnabledInHierarchy(true);
   }
   if(p>=1)this.change(2);
  } else if(this.state!==2){
   this.clipObj.setEnabledInHierarchy(this.hasFace);
   this.cs.rotation=-15;
   this.cs.anchoredPosition=new APJS.Vector2f(Math.min(275,(this.cx+this.hw*0.5-0.5)*720),(this.cy-0.5)*1280);
  }
  for(let i=0;i<this.pool.length;i++){
   if(this.ages[i]<0)continue;
   this.ages[i]+=dt;
   if(this.ages[i]>.75){this.pool[i].setEnabledInHierarchy(false);this.ages[i]=-1;continue;}
   const st=this.transforms[i];const q=st.anchoredPosition;
   st.anchoredPosition=new APJS.Vector2f(q.x+this.velocities[i]*dt,q.y-(140+this.ages[i]*600)*dt);
   st.rotation+=dt*170;
  }
 }
}
