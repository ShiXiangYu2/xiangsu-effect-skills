<!-- Loaded on demand from skills_root/assets/VFXAuthoring/SKILL.md. Read SKILL.md first for the V4 workflow + DSL. This file is the FULL particle-supply-budget model; SKILL.md keeps only the one-line rule + a pointer here. -->

# Particle Supply Budget — the universal conservation law

Every system enforces a particle conservation law. Get this wrong and **spawns
drop silently** — the visible symptom is "bursts work for a moment then stop"
or "rocket explodes but no burst appears, sometimes". The validator
(`SPAWN_DEMAND_EXCEEDS_SUPPLY`) catches the worst cases at `add_vfx_source`
time, but reason about this BEFORE writing system definitions.

This rule applies to **every system, every effect, every trigger kind** — there
is no "rocket-specific" or "fire-specific" version. Effects that look unrelated
(snow accumulation, ball-pit physics, water spray, a single fire emitter) all
use the same three quantities.

## The three quantities

```
self_demand   = spawnRate / delay                    # this system's own spawn loop, per second
inbound       = Σ (event.count × source.death_rate)  # for on_die triggers (count per dying source particle)
                Σ (event.rate × source.alive)        # for rate triggers (per alive source particle)
                Σ (event.count × 60 × source.alive)  # for always triggers (per source per frame, ~60fps)
supply        = capacity / lifetime_min              # max sustainable spawn rate without saturating dead-list
```

**Rule**: `self_demand + inbound ≤ supply` (with a small ~20 % margin for
Poisson burstiness; the validator allows up to 1.2× before throwing).

> **⚠️ Which field carries `self_demand` — `originalSpawnRate` vs `spawnRateMin/Max`.**
> The RUNTIME rate is driven entirely by **`originalSpawnRate`** (particles/sec): the
> controller overwrites `spawnRateMin/Max`+`delayMin/Max` from it every frame, so
> `self_demand ≈ originalSpawnRate` and any `spawnRateMin/Max` you set is ignored at
> runtime (the #1 invisible-effect trap). **`originalSpawnRate: 0` = OFF** (no spawn).
> Caveat for this budget check: the validator currently *estimates* demand from the
> STATIC `spawnRateMin/Max ÷ delay` fields, not from `originalSpawnRate` — so when you
> set `originalSpawnRate` to your target, also mirror that target into `spawnRateMin/Max`
> (with `delay = 1`) so the supply check sees the real demand. The `spawnRate / delay`
> form below describes that static demand estimate.

If you violate this, the engine's dead-list runs empty; subsequent spawn
requests find no slot and are dropped — there is no queue, no retry. The
target system silently produces fewer particles than expected.

**Why `spawnRate / delay` and not just `spawnRate`** — `delay` is **seconds
between spawn batches**, not "the delay before spawning starts". So
`spawnRate=2, delay=0.5` emits 2 particles every 0.5 seconds = 4/sec, not
2/sec. The template's default `delay=1.0` keeps this read-the-numbers obvious;
older `delay=0.0083` defaults (1 frame at 120fps) silently multiplied intended
rates by 120 — that's how the historical Fireworks generation turned
`spawnRate=2` into 240 emits/sec.

## Worked example — Fireworks (rocket → on_die → burst)

```
rocket.spawnRate=1, delay=0.5      → self_demand = 2/sec
rocket.capacity=24, lifetime_min=1 → supply      = 24/sec   ✓ 2 << 24

rocket.events[on_die count=64 → burst]
burst inbound = 64 × rocket.death_rate
              = 64 × min(2, 24) = 128/sec

burst.capacity=200, lifetime_min=1 → supply      = 200/sec  ✓ 128 < 200
```

## Counter-example — the historical Fireworks bug

```
rocket.spawnRate=4, delay=0.008   → self_demand = 500/sec      ❌ trap
rocket.capacity=24, lifetime=1.4   → supply      = 17/sec
   demand 29× over supply — rocket dead-list empties in 48ms,
   subsequent spawns drop silently.

rocket.on_die count=64 → burst inbound = 64 × 17 = 1088/sec
burst.capacity=768, lifetime=1.7   → supply      = 451/sec     ❌
   demand 2.4× over supply — most rocket deaths produce 0 burst particles.
```

## How to fix when the validator throws

- `SPAWN_DEMAND_EXCEEDS_SUPPLY` with dominant=own_spawn → lower `spawnRate`,
  raise `delay`, or raise `capacity` (and possibly `lifetime`).
- Dominant=inbound_event → lower the upstream event's `count` / `rate`, or
  raise THIS system's capacity. The error message proposes a minimum capacity
  that satisfies the math.

> Cross-references: spawn rhythm as a design axis → `references/dimension-basis.md`
> (axis 2/3); event-trigger kinds and the parasitic-default-spawner gotcha →
> `references/events-multisystem.md`.
