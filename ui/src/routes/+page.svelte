<script>
  import { invoke } from '@tauri-apps/api/core';
  import { onMount, onDestroy } from 'svelte';

  let state = {
    mode: 'loading',
    gear: 'loading',
    cpu_pct: 0,
    ram_pct: 0,
    gpu_pct: 0,
    available_ram_gb: 0,
    processes: [],
    dry_run: true,
    ollama_available: false
  };

  let profiles = [];
  let auditLog = [];
  let prefs = {};
  let activeTab = 'dashboard';
  let interval;

  async function loadState() {
    try {
      state = await invoke('get_system_state');
    } catch (e) {
      console.error(e);
    }
  }

  async function loadProfiles() {
    try {
      profiles = await invoke('get_app_profiles');
    } catch (e) {
      console.error(e);
    }
  }

  async function loadAuditLog() {
    try {
      auditLog = await invoke('get_audit_log', { limit: 100 });
    } catch (e) {
      console.error(e);
    }
  }

  async function loadPrefs() {
    try {
      const list = await invoke('get_prefs');
      prefs = Object.fromEntries(list.map(p => [p.key, p.value]));
    } catch (e) {
      console.error(e);
    }
  }

  async function setMode(mode) {
    await invoke('set_pref', { key: 'manual_mode', value: mode });
    await invoke('set_pref', { key: 'manual_mode_set_at', value: new Date().toISOString() });
    await loadPrefs();
  }

  async function setAutonomy(level) {
    await invoke('set_pref', { key: 'autonomy_level', value: level });
    await loadPrefs();
  }

  onMount(() => {
    loadState();
    loadProfiles();
    loadAuditLog();
    loadPrefs();
    interval = setInterval(() => {
      loadState();
      if (activeTab === 'audit') loadAuditLog();
      if (activeTab === 'profiles') loadProfiles();
    }, 5000);
  });

  onDestroy(() => clearInterval(interval));

  function gearColor(gear) {
    if (gear === 'low') return '#4ade80';
    if (gear === 'medium') return '#facc15';
    return '#f87171';
  }

  function modeIcon(mode) {
    if (mode === 'gaming') return '🎮';
    if (mode === 'dev') return '💻';
    if (mode === 'browsing') return '🌐';
    if (mode === 'idle') return '💤';
    return '❓';
  }
</script>

<main>
  <!-- Header -->
  <header>
    <div class="logo">AIOS</div>
    <div class="status-bar">
      {#if state.dry_run}
        <span class="badge dry-run">DRY RUN</span>
      {:else}
        <span class="badge live">LIVE</span>
      {/if}
      <span class="gear-badge" style="color: {gearColor(state.gear)}">
        {state.gear?.toUpperCase()} GEAR
      </span>
    </div>
  </header>

  <!-- Tabs -->
  <nav>
    {#each ['dashboard', 'modes', 'profiles', 'audit', 'settings'] as tab}
      <button
        class="tab {activeTab === tab ? 'active' : ''}"
        on:click={() => { activeTab = tab; if(tab==='audit') loadAuditLog(); if(tab==='profiles') loadProfiles(); }}
      >
        {tab.charAt(0).toUpperCase() + tab.slice(1)}
      </button>
    {/each}
  </nav>

  <!-- Dashboard Tab -->
  {#if activeTab === 'dashboard'}
    <section class="tab-content">
      <div class="mode-display">
        <span class="mode-icon">{modeIcon(state.mode)}</span>
        <div>
          <div class="mode-label">Current mode</div>
          <div class="mode-value">{state.mode}</div>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">CPU</div>
          <div class="stat-value">{state.cpu_pct?.toFixed(1)}%</div>
          <div class="bar"><div class="bar-fill cpu" style="width: {state.cpu_pct}%"></div></div>
        </div>
        <div class="stat-card">
          <div class="stat-label">RAM</div>
          <div class="stat-value">{state.ram_pct?.toFixed(1)}%</div>
          <div class="bar"><div class="bar-fill ram" style="width: {state.ram_pct}%"></div></div>
        </div>
        {#if state.gpu_pct > 0}
        <div class="stat-card">
          <div class="stat-label">GPU</div>
          <div class="stat-value">{state.gpu_pct?.toFixed(1)}%</div>
          <div class="bar"><div class="bar-fill gpu" style="width: {state.gpu_pct}%"></div></div>
        </div>
        {/if}
        <div class="stat-card">
          <div class="stat-label">Available RAM</div>
          <div class="stat-value">{state.available_ram_gb?.toFixed(1)} GB</div>
        </div>
      </div>

      <div class="section-title">Top processes</div>
      <table class="process-table">
        <thead>
          <tr><th>PID</th><th>Name</th><th>CPU%</th><th>RAM MB</th></tr>
        </thead>
        <tbody>
          {#each state.processes as p}
            <tr>
              <td>{p.pid}</td>
              <td>{p.name}</td>
              <td>{p.cpu_pct?.toFixed(1)}</td>
              <td>{p.ram_mb?.toFixed(0)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>

  <!-- Modes Tab -->
  {:else if activeTab === 'modes'}
    <section class="tab-content">
      <div class="section-title">Manual mode</div>
      <div class="mode-grid">
        {#each ['gaming', 'dev', 'browsing', 'idle'] as m}
          <button
            class="mode-btn {prefs.manual_mode === m ? 'selected' : ''}"
            on:click={() => setMode(m)}
          >
            {modeIcon(m)} {m}
          </button>
        {/each}
      </div>
      <button class="clear-btn" on:click={() => setMode('')}>Clear manual mode</button>

      <div class="section-title" style="margin-top: 2rem">Autonomy level</div>
      <div class="autonomy-grid">
        {#each ['conservative', 'balanced', 'aggressive'] as level}
          <button
            class="autonomy-btn {prefs.autonomy_level === level ? 'selected' : ''}"
            on:click={() => setAutonomy(level)}
          >
            {level}
          </button>
        {/each}
      </div>
    </section>

  <!-- Profiles Tab -->
  {:else if activeTab === 'profiles'}
    <section class="tab-content">
      <div class="section-title">App profiles ({profiles.length})</div>
      {#if profiles.length === 0}
        <div class="empty-state">No profiles yet — the agent will build these as apps run.</div>
      {:else}
        <table class="process-table">
          <thead>
            <tr><th>App</th><th>Mode</th><th>CPU avg</th><th>RAM avg</th><th>Sessions</th><th>Override</th></tr>
          </thead>
          <tbody>
            {#each profiles as p}
              <tr class="{p.user_override ? 'override-row' : ''}">
                <td>{p.binary_name}</td>
                <td>{p.mode}</td>
                <td>{p.cpu_avg?.toFixed(1)}%</td>
                <td>{p.ram_avg_mb?.toFixed(0)} MB</td>
                <td>{p.session_count}</td>
                <td>{p.user_override ? '🔒' : ''}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </section>

  <!-- Audit Tab -->
  {:else if activeTab === 'audit'}
    <section class="tab-content">
      <div class="section-title">Audit log (last 100 actions)</div>
      <table class="process-table">
        <thead>
          <tr><th>Time</th><th>Action</th><th>Target</th><th>Mode</th><th>Gear</th><th>Result</th></tr>
        </thead>
        <tbody>
          {#each auditLog as entry}
            <tr>
              <td>{entry.timestamp?.slice(11,19)}</td>
              <td>{entry.action}</td>
              <td>{entry.target}</td>
              <td>{entry.mode}</td>
              <td>{entry.gear}</td>
              <td class="{entry.result === 'ok' ? 'ok' : entry.result === 'dry_run' ? 'dry' : 'err'}">
                {entry.result}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>

  <!-- Settings Tab -->
  {:else if activeTab === 'settings'}
    <section class="tab-content">
      <div class="section-title">User preferences</div>
      <table class="process-table">
        <thead>
          <tr><th>Key</th><th>Value</th></tr>
        </thead>
        <tbody>
          {#each Object.entries(prefs) as [key, value]}
            <tr>
              <td>{key}</td>
              <td>{value}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </section>
  {/if}
</main>

<style>
  :global(html) {
    color-scheme: dark;
  }

  :global(body) {
    margin: 0;
    background: #0f0f0f;
    color: #e2e2e2;
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 14px;
  }

  main {
    max-width: 900px;
    margin: 0 auto;
    padding: 1rem;
  }

  header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
    border-bottom: 1px solid #2a2a2a;
    margin-bottom: 1rem;
  }

  .logo {
    font-size: 1.5rem;
    font-weight: 700;
    color: #a78bfa;
    letter-spacing: 0.2em;
  }

  .status-bar {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .badge {
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .dry-run { background: #422006; color: #fb923c; }
  .live { background: #052e16; color: #4ade80; }

  .gear-badge {
    font-size: 0.75rem;
    font-weight: 600;
  }

  nav {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid #2a2a2a;
    padding-bottom: 0.5rem;
  }

  .tab {
    background: none;
    border: none;
    color: #888;
    padding: 0.4rem 0.8rem;
    cursor: pointer;
    border-radius: 4px;
    font-size: 0.9rem;
  }

  .tab.active {
    background: #1e1e2e;
    color: #a78bfa;
  }

  .tab:hover { color: #e2e2e2; }

  .tab-content { animation: fadein 0.15s ease; }

  @keyframes fadein { from { opacity: 0; } to { opacity: 1; } }

  .mode-display {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: #1e1e2e;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
  }

  .mode-icon { font-size: 2rem; }
  .mode-label { color: #888; font-size: 0.8rem; }
  .mode-value { font-size: 1.4rem; font-weight: 600; color: #a78bfa; text-transform: capitalize; }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .stat-card {
    background: #1e1e2e;
    padding: 1rem;
    border-radius: 8px;
  }

  .stat-label { color: #888; font-size: 0.75rem; margin-bottom: 0.3rem; }
  .stat-value { font-size: 1.2rem; font-weight: 600; margin-bottom: 0.5rem; }

  .bar {
    height: 4px;
    background: #2a2a2a;
    border-radius: 2px;
    overflow: hidden;
  }

  .bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.5s ease;
  }

  .cpu { background: #a78bfa; }
  .ram { background: #60a5fa; }
  .gpu { background: #4ade80; }

  .section-title {
    font-size: 0.8rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.8rem;
  }

  .process-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }

  .process-table th {
    text-align: left;
    color: #888;
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid #2a2a2a;
    font-weight: 500;
  }

  .process-table td {
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid #1a1a1a;
  }

  .process-table tr:hover td { background: #1e1e2e; }

  .override-row td { color: #fb923c; }

  .ok { color: #4ade80; }
  .dry { color: #888; }
  .err { color: #f87171; }

  .mode-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1rem;
  }

  .mode-btn, .autonomy-btn {
    background: #1e1e2e;
    border: 1px solid #2a2a2a;
    color: #e2e2e2;
    padding: 1rem;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.15s;
  }

  .mode-btn.selected, .autonomy-btn.selected {
    border-color: #a78bfa;
    background: #2d2040;
    color: #a78bfa;
  }

  .mode-btn:hover, .autonomy-btn:hover { border-color: #888; }

  .autonomy-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }

  .clear-btn {
    background: none;
    border: 1px solid #2a2a2a;
    color: #888;
    padding: 0.4rem 0.8rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
  }

  .clear-btn:hover { color: #f87171; border-color: #f87171; }

  .empty-state {
    color: #555;
    font-size: 0.9rem;
    padding: 2rem 0;
    text-align: center;
  }
</style>