<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { api, json } from '../api/client';
import type { AgentRun, AgentSource } from '../types';
const emit = defineEmits<{ 'open-bill': [id: string] }>();
const question = ref('统计本月消费最高的房间，并找出金额异常的账单');
const mode = ref<'rules'|'ollama'>('rules');
const result = ref<AgentRun>();
const history = ref<AgentRun[]>([]);
const busy = ref(false), error = ref('');
async function loadHistory() { history.value = await api<AgentRun[]>('/agent/runs'); }
async function perform(fn: () => Promise<void>) {
  if (busy.value) return;
  busy.value = true; error.value = '';
  try { await fn(); } catch(e) { error.value = e instanceof Error ? e.message : '操作失败'; }
  finally { busy.value = false; }
}
async function ask() {
  await perform(async () => { result.value = await api<AgentRun>('/agent/runs', json('POST', { question: question.value, mode: mode.value })); await loadHistory(); });
}
function retry() { perform(async () => { if(result.value) result.value = await api<AgentRun>(`/agent/runs/${result.value.id}/retry`, {method:'POST'}); await loadHistory(); }); }
function sourceClick(source: AgentSource) {
  if (source.kind === 'bill' && source.id) emit('open-bill', source.id);
  else if(source.url) window.open(source.url, '_blank', 'noopener');
}
onMounted(() => perform(loadHistory));
</script>
<template>
  <section>
    <h2>本地业务分析</h2>
    <p class="muted">金额由数据库计算，回答附查询口径和来源。仅支持只读分析，修改账单请进入详情。</p>
    <select v-model="mode" :disabled="busy"><option value="rules">规则查询（无需大模型）</option><option value="ollama">本机 Ollama 模型规划（需配置）</option></select>
    <textarea v-model="question" maxlength="1000" rows="3" :disabled="busy" placeholder="例如：统计本月实收合计，并列出异常账单"></textarea>
    <button @click="ask" :disabled="busy || !question.trim()">{{busy?'正在执行…':'开始分析'}}</button>
    <p v-if="error" class="notice" role="alert">{{error}}</p>
  </section>
  <section v-if="result">
    <h2>{{result.mode==='rules'?'规则查询结果':'本地模型规划结果'}}</h2>
    <p class="muted">{{result.status}} · {{result.created_at}}</p>
    <pre>{{result.answer || result.error_message}}</pre>
    <a v-if="result.status==='completed'" :href="`/api/v1/agent/runs/${result.id}/report`">下载 Markdown 报告</a>
    <button v-if="['failed','interrupted'].includes(result.status)" @click="retry" :disabled="busy">从已保存进度重试</button>
    <h3>数据来源</h3>
    <div v-for="(source,index) in result.sources" :key="index"><button v-if="source.url" class="small" @click="sourceClick(source)">{{source.label}}</button><p v-else>{{source.label}} · {{source.start}} — {{source.end}}</p></div>
    <details><summary>执行日志</summary><p v-for="step in result.steps" :key="step.id">{{step.node}} / {{step.tool || '—'}} · {{step.status}} · {{step.elapsed_ms}} ms {{step.error_message}}</p></details>
  </section>
  <section><h2>最近分析</h2><button v-for="run in history" :key="run.id" :disabled="busy" @click="perform(async()=>{result=await api<AgentRun>('/agent/runs/'+run.id)})">{{run.question}} · {{run.status}}</button><p v-if="!history.length" class="muted">还没有分析记录。</p></section>
</template>
<style scoped>
textarea {display:block;width:100%;margin:18px 0;padding:14px;border:1px solid #cddbd4;border-radius:8px;font:inherit;resize:vertical}
select {padding:10px;border:1px solid #cddbd4;border-radius:6px}h3{margin-top:26px;font-size:16px}section>button{margin:6px 10px 6px 0}details{margin-top:24px}
</style>
