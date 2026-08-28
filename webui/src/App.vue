<script setup lang="ts">
import { onMounted } from 'vue'
import TopBar from './components/TopBar.vue'
import SourcePanel from './components/SourcePanel.vue'
import Timeline from './components/Timeline.vue'
import Transcript from './components/Transcript.vue'
import StatusBar from './components/StatusBar.vue'
import { store } from './store'
import { loadModels } from './controller'

onMounted(() => {
  void loadModels()
})
</script>

<template>
  <div class="app">
    <TopBar />
    <SourcePanel />

    <div v-if="store.error" class="error-banner" role="alert">
      <span class="err-ico">!</span>
      <span class="err-msg">{{ store.error }}</span>
      <button class="err-close" @click="store.error = null">×</button>
    </div>

    <main class="workspace">
      <Timeline />
      <Transcript />
    </main>

    <StatusBar />
  </div>
</template>

<style scoped>
.app {
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  padding: 12px 16px;
  gap: 12px;
  max-width: 1500px;
  margin: 0 auto;
}

.error-banner {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: var(--radius-sm);
  padding: 8px 14px;
  color: var(--danger);
  animation: slideDown 0.25s ease;
}

.err-ico {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--danger);
  color: #fff;
  font-weight: 700;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.err-msg {
  flex: 1;
}

.err-close {
  padding: 2px 10px;
  background: transparent;
  border: none;
  font-size: 18px;
  line-height: 1;
  color: var(--danger);
}

.workspace {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(0, 2fr);
  gap: 12px;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1080px) {
  .app {
    padding: 8px 10px;
    gap: 8px;
  }

  .workspace {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(0, 1fr) minmax(0, 1fr);
    overflow: hidden;
  }
}
</style>
