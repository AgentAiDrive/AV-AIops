// apps/av-wizard/pages/recipes.js
import { put } from '../db/store.js';

const PRESETS = [
  { id:"baseline_control",
    name:"Baseline Control",
    hypothesis:"Current standard scene establishes baseline for lift comparisons.",
    knobs:{ preset:"Baseline" },
    metrics:{ primary:"decision_reached", secondary:["followup_booked","csat","engagement_proxy"] },
    guardrails:{ rollback_if:"issue_rate_per_100 > baseline*1.20 || csat < 7.0", max_step_change:0.10 },
    risk:"low",
    tags:["control","global"]
  },
  { id:"lighting_neutral_presentations",
    name:"Neutral Presentation Lighting",
    hypothesis:"Neutral CT (~4000K) at ~70% improves readability.",
    knobs:{ lighting:{ ct_kelvin:4000, level:0.70, audience_wash_delta:-0.10, apply_during:"slides" } },
    metrics:{ primary:"decision_reached", secondary:["csat","followup_booked"] },
    guardrails:{ rollback_if:"csat < 7.0 || issue_rate_per_100 > baseline*1.20", max_step_change:0.10 },
    risk:"low",
    tags:["lighting","global"]
  },
  { id:"audio_qna_gain_boost",
    name:"Audience Q&A Gain Boost",
    hypothesis:"+3 dB audience gain with slightly lower expander threshold increases Q&A participation.",
    knobs:{ audio:{ audience_mic_gain_db:3, expander_threshold_db:-2, autogate_bias:0 } },
    metrics:{ primary:"engagement_proxy", secondary:["decision_reached","csat"] },
    guardrails:{ rollback_if:"feedback_events > baseline || csat < 7.0", max_step_change:0.10 },
    risk:"medium",
    tags:["audio","global"]
  },
  { id:"hq_aud1_lighting_focus",
    name:"HQ-AUD-1 — Lighting Focus",
    hypothesis:"Tighter neutral CT band and level control raises decision clarity in HQ-AUD-1.",
    knobs:{ lighting:{ ct_band_kelvin:[3800,4200], level:0.70, audience_wash_delta:-0.10 } },
    metrics:{ primary:"decision_reached", secondary:["csat"] },
    guardrails:{ rollback_if:"csat < 7.0", max_step_change:0.10 },
    risk:"low",
    applies_to:["HQ-AUD-1"],
    tags:["lighting","room-overlay"]
  },
  { id:"nyc_th2_audio_focus",
    name:"NYC-TH-2 — Audio/Q&A Focus",
    hypothesis:"+3 dB audience gain, expander −2 dB, 2-speaker autogate bias increases Q&A without feedback.",
    knobs:{ audio:{ audience_mic_gain_db:3, expander_threshold_db:-2, autogate_bias:2 } },
    metrics:{ primary:"engagement_proxy", secondary:["csat","decision_reached"] },
    guardrails:{ rollback_if:"feedback_events > baseline || csat < 7.0", max_step_change:0.10 },
    risk:"medium",
    applies_to:["NYC-TH-2"],
    tags:["audio","room-overlay"]
  },
  { id:"ebc_exec1_presenter_confidence",
    name:"EBC-EXEC-1 — Presenter Confidence",
    hypothesis:"Lectern +2 dB, warm camera preset, −5% audience wash at slide start improves confidence & clarity.",
    knobs:{ audio:{ lectern_mic_gain_db:2 }, camera:{ preset:"Presenter A", tint:"warm" }, lighting:{ audience_wash_delta:-0.05, apply_on:"slide_start" } },
    metrics:{ primary:"decision_reached", secondary:["csat","followup_booked"] },
    guardrails:{ rollback_if:"csat < 7.0 || join_latency_s > baseline + 5", max_step_change:0.10 },
    risk:"low",
    applies_to:["EBC-EXEC-1"],
    tags:["mixed","room-overlay"]
  },

  // ---------- NEW CARDS ----------
  { id:"decision_close_warm_reinforcement",
    name:"Decision Close — Warm Reinforcement",
    hypothesis:"Slightly warmer CT and a small level boost during the decision phase increases commitment.",
    knobs:{ lighting:{ ct_kelvin:3500, level_delta:0.05, apply_on:"decision_phase" } },
    metrics:{ primary:"decision_reached", secondary:["csat","followup_booked"] },
    guardrails:{ rollback_if:"csat < 7.0", max_step_change:0.10 },
    risk:"low",
    tags:["lighting","phase"]
  },
  { id:"tech_deepdive_cooler_focus",
    name:"Tech Deep-Dive — Cooler Focus",
    hypothesis:"Cooler CT around 4600K improves technical detail perception during deep-dives.",
    knobs:{ lighting:{ ct_kelvin:4600, level:0.70, apply_during:"deep_dive" } },
    metrics:{ primary:"decision_reached", secondary:["csat"] },
    guardrails:{ rollback_if:"csat < 7.0", max_step_change:0.10 },
    risk:"low",
    tags:["lighting","phase"]
  },
  { id:"camera_presenter_eye_level",
    name:"Presenter Eye-Level Framing",
    hypothesis:"Eye-level framing reduces cognitive strain and raises presenter trust.",
    knobs:{ camera:{ framing:"eye_level", preset:"Presenter A" } },
    metrics:{ primary:"csat", secondary:["decision_reached"] },
    guardrails:{ rollback_if:"csat < 7.0", max_step_change:0.10 },
    risk:"low",
    tags:["camera"]
  },
  { id:"camera_qna_cutaways",
    name:"Audience Cutaways during Q&A",
    hypothesis:"Periodic audience cutaways increase engagement and perceived participation.",
    knobs:{ camera:{ auto_cutaway:true, interval_s:45 } },
    metrics:{ primary:"engagement_proxy", secondary:["csat"] },
    guardrails:{ rollback_if:"issue_rate_per_100 > baseline*1.20", max_step_change:0.10 },
    risk:"low",
    tags:["camera","qna"]
  },
  { id:"audio_speech_intelligibility_eq",
    name:"Speech Intelligibility EQ",
    hypothesis:"Gentle mid-high boost increases intelligibility without fatigue.",
    knobs:{ audio:{ eq_mid_hi_db:2, comp_threshold_db:-12 } },
    metrics:{ primary:"decision_reached", secondary:["csat"] },
    guardrails:{ rollback_if:"feedback_events > baseline || csat < 7.0", max_step_change:0.10 },
    risk:"low",
    tags:["audio"]
  },
  { id:"audio_deesser_sibilance_control",
    name:"De-Esser Sibilance Control",
    hypothesis:"Reducing sibilance improves listener comfort and CSAT.",
    knobs:{ audio:{ deesser_threshold_db:-18 } },
    metrics:{ primary:"csat", secondary:["decision_reached"] },
    guardrails:{ rollback_if:"csat < 7.0", max_step_change:0.10 },
    risk:"low",
    tags:["audio"]
  },
  { id:"hybrid_remote_echo_guard",
    name:"Hybrid — Echo Guard",
    hypothesis:"Stronger AEC/aggressiveness reduces echo complaints in hybrid meetings.",
    knobs:{ audio:{ aec_aggressiveness:"high", far_end_echo_guard:true } },
    metrics:{ primary:"issue_rate_per_100", secondary:["csat"] },
    guardrails:{ rollback_if:"issue_rate_per_100 > baseline*1.20 || csat < 7.0", max_step_change:0.10 },
    risk:"medium",
    tags:["audio","hybrid"]
  },
  { id:"transition_bookends_cues",
    name:"Open/Close Bookends — Cues",
    hypothesis:"Subtle walk-in/out cues improve emotional cadence and CSAT.",
    knobs:{ transitions:{ music_cue:true, open_volume:0.20, close_volume:0.15, fade_s:4 } },
    metrics:{ primary:"csat", secondary:["followup_booked"] },
    guardrails:{ rollback_if:"csat < 7.0", max_step_change:0.10 },
    risk:"low",
    tags:["experience"]
  },
  { id:"prejoin_healthcheck_10min",
    name:"Pre-Join Healthcheck (10 min)",
    hypothesis:"Automated checks 10 minutes prior reduce join latency and incident rate.",
    knobs:{ prejoin:{ enabled:true, check_minutes_before:10 } },
    metrics:{ primary:"join_latency_s", secondary:["issue_rate_per_100","csat"] },
    guardrails:{ rollback_if:"issue_rate_per_100 > baseline*1.20", max_step_change:0.10 },
    risk:"low",
    tags:["ops"]
  },
  { id:"qna_mic_runner_mode",
    name:"Q&A — Mic Runner Mode",
    hypothesis:"Designated runners with gentle gating reduces overlap and increases participation.",
    knobs:{ audio:{ mic_runner_mode:true, runner_mics:2, gate_release_ms:250 } },
    metrics:{ primary:"engagement_proxy", secondary:["csat"] },
    guardrails:{ rollback_if:"feedback_events > baseline || csat < 7.0", max_step_change:0.10 },
    risk:"medium",
    tags:["audio","qna"]
  },
  { id:"remote_qna_moderation",
    name:"Remote Q&A Moderation Hold",
    hypothesis:"A short moderation hold reduces disruptions and keeps meeting flow.",
    knobs:{ remote_qna:{ moderation:"enabled", hold_time_s:10 } },
    metrics:{ primary:"engagement_proxy", secondary:["csat","decision_reached"] },
    guardrails:{ rollback_if:"csat < 7.0", max_step_change:0.10 },
    risk:"low",
    tags:["qna","hybrid"]
  },
  { id:"lighting_slide_focus_dimming",
    name:"Slide Focus Dimming",
    hypothesis:"A subtle −6% overall dim during slides improves readability without harming CSAT.",
    knobs:{ lighting:{ overall_level_delta:-0.06, apply_during:"slides" } },
    metrics:{ primary:"decision_reached", secondary:["csat"] },
    guardrails:{ rollback_if:"csat < 7.0 || issue_rate_per_100 > baseline*1.20", max_step_change:0.10 },
    risk:"low",
    tags:["lighting"]
  }
]; // <-- this was missing

export function Recipes(){
  const div = document.createElement('div');
  const cards = PRESETS.map(r => `
    <div class="card">
      <b>${r.name}</b>
      <div class="muted">${r.hypothesis}</div>
      <button class="btn add" data-id="${r.id}" aria-label="Add recipe ${r.name}" title="Add ${r.name}">Add</button>
    </div>`).join('');
  div.innerHTML = `<h2>Recipes</h2><div class="grid grid-2">${cards}</div>`;

  div.addEventListener('click', async (e) => {
    const b = e.target.closest('.add'); 
    if (!b) return;
    const r = PRESETS.find(x => x.id === b.dataset.id);
    try {
      await put('recipes', { id: r.id, ...r, created_at: Date.now() });
      b.disabled = true; 
      b.textContent = 'Added';
    } catch (err) {
      console.error('Failed to add recipe', err);
      b.textContent = 'Retry';
    }
  });

  return div;
}
