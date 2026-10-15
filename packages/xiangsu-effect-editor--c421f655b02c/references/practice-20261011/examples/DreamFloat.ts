@component()
export class DreamFloat extends APJS.BasicScriptComponent {
  private elapsed: number = 0;
  private ready: boolean = false;
  private st!: APJS.ScreenTransform;
  private origin!: APJS.Vector2f;
  private angle: number = 0;
  onStart(): void {
    const st = this.getSceneObject().getComponent("ScreenTransform") as APJS.ScreenTransform;
    if (!st) return;
    this.st = st;
    const p = st.anchoredPosition;
    this.origin = new APJS.Vector2f(p.x, p.y);
    this.angle = st.rotation;
    this.ready = true;
    console.log("[state] DreamFloat started " + this.getSceneObject().name);
  }
  onUpdate(dt: number): void {
    if (!this.ready) return;
    this.elapsed += dt;
    const phase = this.origin.x * 0.013;
    this.st.anchoredPosition = new APJS.Vector2f(this.origin.x + Math.sin(this.elapsed * 0.55 + phase) * 6, this.origin.y + Math.sin(this.elapsed * 0.8 + phase) * 10);
    this.st.rotation = this.angle + Math.sin(this.elapsed * 0.65 + phase) * 7;
  }
}
