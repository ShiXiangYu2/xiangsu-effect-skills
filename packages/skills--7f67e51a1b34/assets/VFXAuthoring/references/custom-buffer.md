<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first. -->

# Custom Buffer (VFXBuffer) — GPU particles → CPU/game logic

A **custom buffer** is one persistent INT GPU buffer the particle shader
`atomicAdd`s into, and a **script reads back live** each frame. It is the only
channel that lets thousands of GPU particles report an aggregate fact (how many
hit a target, a score, a kill count) to CPU/game logic — the GPU can't otherwise
tell the CPU "N of my particles did X".

Canonical use: **particles as projectiles / detectors**, the buffer as the
**scoreboard**. (Reference: the shipped "Snow_VFXBuffers" effect — snow hits a
cloud/snowman, the buffer counts hits, a script drives their health.)

> When to use it: any "shoot/hit/collect/count → something reacts" effect, a
> score/combo counter, a health bar driven by particle impacts, a threshold
> trigger ("when 100 particles have landed, do Y"). If nothing on the CPU needs
> to KNOW a particle count, you don't need a buffer.

---

## 1. Author the buffer (write side)

Declare it in a system's `runtime` — **omit `guid`**, the server auto-creates the
`.vfxbuffer` resource and fills it (you cannot supply a guid yourself):

```json
"runtime": {
  "custom_buffers": [{"fields": ["hits"]}]
}
```

`fields` names the INT slots (slot 0 = `fields[0]`, etc.). One INT buffer per
system (V1). The shader gets a `vfx_custom_buffer` SSBO; the importer binds it.

**To count INTO a slot, use a writer** (these atomicAdd 1 per event):

| Want to count… | Declare |
|---|---|
| particles entering a region (a target hitbox) | `kill_volume:[{shape:'sphere',center:[x,y,z],radius:r}]` + `kill_count_into:"<field>"` — the particle is killed AND counted (a consumed projectile) |
| particles bouncing off a surface | `bounce:[…]` + `bounce_count_into:"<field>"` |

`kill_count_into`/`bounce_count_into` name a field from `custom_buffers[0].fields`.
For "bullets hit enemy", put a `kill_volume` sphere at the enemy and
`kill_count_into` a `hits` field — each bullet that reaches the enemy is consumed
and counted.

> Counting a slot WITHOUT killing/bouncing (e.g. particles passing through a
> zone, or per-frame stats) needs a shader edit (atomicAdd into
> `vfx_custom_buffer_buf[slot]` in update.comp). Not covered by a writer yet.

**Semantics — counts are CUMULATIVE.** atomicAdd accumulates; the buffer is reset
only on effect reset (loop/restart), NOT per frame. So a counter only ever rises
during a run. Design game logic around totals (`health = max(0, 1 - hits/MAX)`),
not per-frame deltas.

---

## 2. Read the buffer in a script (consumer side)

Add a script (`add_script`) and attach it (`add_component type=<Class>`)
to **an object that can reach the VFX**. Read pattern (verified live — the device
d.ts is thin/misleading here, use exactly this):

```ts
@component()
export class EnemyHealth extends APJS.BasicScriptComponent {
  private _vfx: any = null;
  onStart(): void {
    // the VisualEffect component (same object, or a child/sibling you reach)
    this._vfx = this.getSceneObject().getComponent("VisualEffect");
  }
  onUpdate(dt: number): void {
    if (!this._vfx) return;
    const a = this._vfx.asset;              // .asset = the VisualEffectAsset (profile)
    if (!a || !a.contextBlocks) return;
    let hits = -1;
    const cbs = a.contextBlocks;            // iterate the PROFILE contexts
    for (let i = 0; i < cbs.length; i++) {
      const m = cbs[i] ? cbs[i].customBufferMap : null;
      if (m && m.has("vfx_custom_buffer")) {           // ALWAYS has() before get()
        const buf = m.get("vfx_custom_buffer");
        if (buf && buf.data && buf.data.size() > 0) { hits = buf.data.get(0); break; }
      }
    }
    if (hits < 0) return;
    // … drive game state from `hits` (slot 0 = fields[0]) …
  }
}
```

**Landmines (each cost a debugging cycle — do exactly this):**
- Use **`comp.asset`**, NOT `comp.profile` — `.profile` is `null` from a host
  script (only the VFX's own generated controller sees it).
- Iterate **`asset.contextBlocks[i]`**, NOT `comp.getCtxBlockWithID(i)` — the live
  instance contexts do NOT carry `customBufferMap`; the profile contexts do.
- **ALWAYS `has()` before `get()`** — the engine `Map.get()` inserts a null entry
  on a missing key → SIGSEGV on scene teardown.
- The engine maps GPU→`.data` every frame, so `.data` is live; the slot index is
  the field's position in `fields`.

**Reaching the VFX from another object:** if the reader script is NOT on the VFX
object, parent the objects and use `getSceneObject().getChild("name")` /
`.parent` (`SceneObject` has `getChild`/`getChildren`/`parent`/`getComponent`).

---

## 3. Worked example — bullets attack an enemy

Goal: bullets fly at an enemy; each hit damages it; it's destroyed at full damage.

1. **Bullets** = a StandardQuad whose velocity is edited to fire toward the enemy
   (`edit_vfx_source` the init.comp VELOCITY block: `vx = speed; vy = small spread;
   vz = 0;`). Place the emitter at the origin.
2. **Hit counting**: a `kill_volume` sphere AT the enemy position + `kill_count_into:"hits"`
   + `custom_buffers:[{fields:["hits"]}]`. Each bullet reaching the enemy is
   consumed and counted.
3. **Enemy** = a visible object (e.g. an `Image`) at the target position, a child
   of the emitter so the script can `getChild("enemy")`.
4. **Script** on the emitter: read `hits` (section 2) → `health = max(0, 1 - hits/MAX)`
   → set the enemy's `Transform.localScale` to `base * health` (it shrinks as it
   takes damage and vanishes — destroyed — at `health == 0`).

Verified: `hits 0→18→36→54`, `health 1.00→0.64→0.28→0.00`, enemy shrinks then
disappears. The whole damage system is GPU-counted and CPU-driven through the
buffer.

> The buffer is NOT panel-exposed — it's a script-read runtime channel, not a
> user-tunable parameter. Don't expect it in the asset inspector.
