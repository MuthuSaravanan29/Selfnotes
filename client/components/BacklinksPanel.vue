<template>
  <div v-if="backlinks.length > 0" class="mt-8 border-t border-theme-border pt-4">
    <h3 class="mb-2 text-xs font-bold uppercase tracking-wider text-theme-text-very-muted">
      {{ backlinks.length }} {{ backlinks.length === 1 ? "backlink" : "backlinks" }}
    </h3>
    <div
      v-for="title in backlinks"
      :key="title"
      class="group flex cursor-pointer items-center rounded px-2 py-1.5 text-sm hover:bg-theme-background-elevated"
      @click="navigateTo(title)"
    >
      <SvgIcon
        type="mdi"
        :path="mdiLinkVariant"
        size="1em"
        class="mr-2 shrink-0 text-theme-text-very-muted"
      />
      <span class="text-theme-text hover:text-theme-brand">{{ title }}</span>
    </div>
  </div>
</template>

<script setup>
import { mdiLinkVariant } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";
import { ref, watch } from "vue";
import { useRouter } from "vue-router";

import { getBacklinks } from "../api.js";
import { useGlobalStore } from "../globalStore.js";

const props = defineProps({ title: String });
const router = useRouter();
const globalStore = useGlobalStore();
const backlinks = ref([]);

async function fetchBacklinks() {
  if (!props.title) {
    backlinks.value = [];
    return;
  }
  try {
    backlinks.value = await getBacklinks(props.title);
  } catch {
    backlinks.value = [];
  }
}

function navigateTo(title) {
  globalStore.currentNoteTitle = title;
  router.push({ name: "note", params: { title } });
}

watch(() => props.title, fetchBacklinks, { immediate: true });
</script>
