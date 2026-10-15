@component()
export class SpiderCrawl extends APJS.BasicScriptComponent {
 @serializeProperty spider: APJS.SceneObject;
 @serializeProperty previewTime: number = -1;
 private mesh: APJS.Mesh;
 private animator: APJS.Animator;
 private vertices: Float32Array;
 private indices: Uint16Array;
 private stride:number=0;
 private normalOffset:number=0;
 private ready:boolean=false;
 private elapsed:number=0;
 private lastPhase:number=-1;
 private lost:boolean=false;
 private bindings:number[][]=[];
 private lengths:number[]=[];
 private total:number=0;
 private static readonly SPEED:number=6.3;
 private static readonly SIZE:number=1.26;
 private lastLoop:number=-1;
 private points:APJS.Vector3f[]=[];
 private record=(_e:APJS.IEvent):void=>{this.elapsed=0;this.lastPhase=-1;this.lastLoop=-1;console.log("[Spider] record reset");};
 onStart():void{APJS.EventManager.getGlobalEmitter().on(APJS.EventType.RecordStart,this.record,this);}
 onDestroy():void{APJS.EventManager.getGlobalEmitter().off(APJS.EventType.RecordStart,this.record,this);}
 private v(x:number,y:number,z:number):APJS.Vector3f{return new APJS.Vector3f(x,y,z);}
 private pos(i:number):APJS.Vector3f{const j=i*this.stride;return this.v(this.vertices[j],this.vertices[j+1],this.vertices[j+2]);}
 private cat(a:APJS.Vector3f,b:APJS.Vector3f,c:APJS.Vector3f,d:APJS.Vector3f,t:number):APJS.Vector3f{
  const t2=t*t,t3=t2*t;
  return this.v(.5*(2*b.x+(-a.x+c.x)*t+(2*a.x-5*b.x+4*c.x-d.x)*t2+(-a.x+3*b.x-3*c.x+d.x)*t3),.5*(2*b.y+(-a.y+c.y)*t+(2*a.y-5*b.y+4*c.y-d.y)*t2+(-a.y+3*b.y-3*c.y+d.y)*t3),.5*(2*b.z+(-a.z+c.z)*t+(2*a.z-5*b.z+4*c.z-d.z)*t2+(-a.z+3*b.z-3*c.z+d.z)*t3));
 }
 private bind(q:APJS.Vector3f):number[]{
  const ox=0,oy=1,oz=-5,dx=q.x,dy=q.y-oy,dz=q.z-oz;
  let best=999;let found:number[]=[];
  const vv=this.vertices,ss=this.stride,ii=this.indices;
  for(let k=0;k<ii.length;k+=3){
   const ia=ii[k]*ss,ib=ii[k+1]*ss,ic=ii[k+2]*ss;
   const ax=vv[ia],ay=vv[ia+1],az=vv[ia+2];
   const ex=vv[ib]-ax,ey=vv[ib+1]-ay,ez=vv[ib+2]-az;
   const fx=vv[ic]-ax,fy=vv[ic+1]-ay,fz=vv[ic+2]-az;
   const hx=dy*fz-dz*fy,hy=dz*fx-dx*fz,hz=dx*fy-dy*fx;
   const det=ex*hx+ey*hy+ez*hz;if(Math.abs(det)<.000001)continue;
   const inv=1/det,sx=ox-ax,sy=oy-ay,sz=oz-az;
   const u=(sx*hx+sy*hy+sz*hz)*inv;if(u<0||u>1)continue;
   const qx=sy*ez-sz*ey,qy=sz*ex-sx*ez,qz=sx*ey-sy*ex;
   const v=(dx*qx+dy*qy+dz*qz)*inv;if(v<0||u+v>1)continue;
   const t=(fx*qx+fy*qy+fz*qz)*inv;
   if(t>.001&&t<best){best=t;found=[ii[k],ii[k+1],ii[k+2],1-u-v,u,v];}
  }
  return found;
 }
 private read(b:number[],normal:boolean):APJS.Vector3f{
  const off=normal?this.normalOffset:0;let x=0,y=0,z=0;
  for(let k=0;k<3;k++){const j=b[k]*this.stride+off,w=b[k+3];x+=this.vertices[j]*w;y+=this.vertices[j+1]*w;z+=this.vertices[j+2]*w;}
  const a=this.v(x,y,z);if(normal)a.normalize();return a;
 }
 private initialize():void{
  if(!this.spider||APJS.AlgorithmManager.getResult().getFaceCount()===0)return;
  const mr=this.getSceneObject().getComponent("MeshRenderer") as APJS.MeshRenderer;
  if(!mr||!mr.mesh||mr.mesh.getVertexCount()<10)return;
  this.mesh=mr.mesh;this.vertices=this.mesh.getVertices();this.indices=this.mesh.getTriangles();
  const attrs=this.mesh.getVertexAttributes();this.stride=0;
  for(let i=0;i<attrs.length;i++){if(attrs[i].attribute===APJS.VertexAttributeType.Normal)this.normalOffset=this.stride;this.stride+=(attrs[i].componentCount||0);}
  this.bindings=[];this.lengths=[];this.total=0;
  const raw=[[0,-.4,8],[1.5,-1.8,6.5],[3,-4,5],[2,-5.6,5],[0,-6.0,5],[3,-5.8,4],[6,-4,2],[6.8,1,2],[6,5,2],[4,8,2],[1,11,0],[0,13,-3],[-2,12,-1],[-4,9,1],[-6,5,2],[-5.8,1.5,3],[-4,-1,5],[-2.3,.4,6.2],[-1.1,.7,7.1]];
  this.points=raw.map(p=>this.v(p[0],p[1],p[2]));
  for(let s=0;s<this.points.length;s++){
   for(let j=0;j<16;j++){
    const q=this.cat(this.points[(s+this.points.length-1)%this.points.length],this.points[s],this.points[(s+1)%this.points.length],this.points[(s+2)%this.points.length],j/16);
    const b=this.bind(q);if(b.length===0){console.log("[Spider] surface miss "+s);return;}
    this.bindings.push(b);
    if(this.bindings.length>1){const a=this.read(this.bindings[this.bindings.length-2],false),c=this.read(b,false);this.total+=Math.sqrt((a.x-c.x)*(a.x-c.x)+(a.y-c.y)*(a.y-c.y)+(a.z-c.z)*(a.z-c.z));}
    this.lengths.push(this.total);
   }
  }
  const end=this.read(this.bindings[this.bindings.length-1],false),start=this.read(this.bindings[0],false);
  this.total+=Math.sqrt((end.x-start.x)*(end.x-start.x)+(end.y-start.y)*(end.y-start.y)+(end.z-start.z)*(end.z-start.z));
  this.bindings.push(this.bindings[0]);this.lengths.push(this.total);
  this.animator=this.spider.getComponent("Animator") as APJS.Animator;
  if(this.animator&&this.animator.animations.length>0){this.animator.play(this.animator.animations[0].name,APJS.AnimationWrapMode.Repeat,3.3);console.log("[Spider] walk "+this.animator.animations[0].name);}
  this.spider.getTransform().localScale=this.v(SpiderCrawl.SIZE,SpiderCrawl.SIZE,SpiderCrawl.SIZE);
  this.ready=true;console.log("[Spider] surface ready samples="+this.bindings.length+" length="+this.total+" period="+this.total/SpiderCrawl.SPEED);
 }
 private sample(distance:number,normal:boolean):APJS.Vector3f{
  const d=((distance%this.total)+this.total)%this.total;let i=0;
  while(i<this.lengths.length-2&&this.lengths[i+1]<d)i++;
  const t=(d-this.lengths[i])/Math.max(.0001,this.lengths[i+1]-this.lengths[i]);
  return APJS.Vector3f.lerp(this.read(this.bindings[i],normal),this.read(this.bindings[i+1],normal),t);
 }
 onUpdate(dt:number):void{
  if(!this.ready){this.initialize();return;}
  if(APJS.AlgorithmManager.getResult().getFaceCount()===0){
   this.spider.setEnabledInHierarchy(false);
   if(!this.lost){this.lost=true;if(this.animator)this.animator.pauseAll();console.log("[Spider] no face paused");}
   return;
  }
  if(this.lost){this.lost=false;if(this.animator)this.animator.resumeAll();console.log("[Spider] face resumed");}
  this.vertices=this.mesh.getVertices();
  this.elapsed+=Math.min(dt,.2);
  const t=this.previewTime>=0?this.previewTime:this.elapsed;
  const traveled=t*SpiderCrawl.SPEED;
  const d=traveled%this.total;
  const loop=Math.floor(traveled/this.total);
  this.spider.setEnabledInHierarchy(true);
  if(loop!==this.lastLoop){this.lastLoop=loop;console.log("[Spider] continuous loop="+loop+" period="+this.total/SpiderCrawl.SPEED);}
  const phase=Math.floor(d/this.total*4);
  if(phase!==this.lastPhase){this.lastPhase=phase;console.log("[Spider] loop quarter="+phase);}
  const p=this.sample(d,false),n=this.sample(d,true);n.normalize();
  const a=this.sample(d-.1,false),b=this.sample(d+.1,false);
  const tangent=this.v(b.x-a.x,b.y-a.y,b.z-a.z);tangent.normalize();
  const tr=this.spider.getTransform();
  const q=APJS.Quaternionf.lookAt(n,tangent);
  tr.localRotation=APJS.Quaternionf.slerp(tr.localRotation,q,Math.min(1,dt*18));
  const lift=.18+Math.sin(this.elapsed*24)*.025;
  tr.localPosition=this.v(p.x+n.x*lift,p.y+n.y*lift,p.z+n.z*lift);
 }
}
