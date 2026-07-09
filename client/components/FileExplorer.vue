<template>
  <aside
    class="flex h-full flex-col border-r border-theme-border bg-theme-background"
    :class="visible ? 'w-64' : 'w-0 overflow-hidden'"
  >
    <div class="flex items-center justify-between border-b border-theme-border px-3 py-2">
      <span class="text-sm font-semibold text-theme-text-muted">NOTES</span>
      <button
        class="rounded p-1 text-theme-text-muted hover:bg-theme-background-elevated"
        @click="toggleSidebar"
        title="Close sidebar"
      >
        <SvgIcon type="mdi" :path="mdiChevronLeft" size="1.25em" />
      </button>
    </div>

    <div class="border-b border-theme-border px-2 py-2">
      <input
        v-model="filterText"
        type="text"
        placeholder="Filter..."
        class="w-full rounded border border-theme-border bg-theme-background-elevated px-2 py-1 text-sm text-theme-text outline-none placeholder:text-theme-text-very-muted focus:border-theme-brand"
      />
    </div>

    <div class="flex-1 overflow-y-auto">
      <div v-if="filteredNotes.length === 0" class="px-3 py-4 text-center text-sm text-theme-text-very-muted">
        No notes found
      </div>
      <div
        v-for="note in filteredNotes"
        :key="note.title"
        class="group flex cursor-pointer items-center px-3 py-1.5 text-sm"
        :class="isActive(note.title) ? 'bg-theme-brand/10 text-theme-brand' : 'text-theme-text hover:bg-theme-background-elevated'"
        @click="openNote(note.title)"
      >
        <SvgIcon
          type="mdi"
          :path="mdiFileDocumentOutline"
          size="1em"
          class="mr-2 shrink-0"
          :class="isActive(note.title) ? 'text-theme-brand' : 'text-theme-text-muted'"
        />
        <span class="truncate">{{ note.title }}</span>
      </div>
    </div>

    <!-- Tags Section -->
    <div v-if="tags.length > 0" class="border-t border-theme-border">
      <button
        class="flex w-full items-center px-3 py-2 text-xs font-semibold uppercase text-theme-text-very-muted hover:bg-theme-background-elevated"
        @click="tagsExpanded = !tagsExpanded"
      >
        <SvgIcon
          type="mdi"
          :path="tagsExpanded ? mdiChevronDown : mdiChevronRight"
          size="1em"
          class="mr-1"
        />
        TAGS ({{ tags.length }})
      </button>
      <div v-if="tagsExpanded" class="max-h-48 overflow-y-auto px-2 pb-2">
        <div
          v-for="tag in tags"
          :key="tag"
          class="group flex cursor-pointer items-center rounded px-2 py-1 text-sm text-theme-text-muted hover:bg-theme-background-elevated hover:text-theme-text"
          @click="searchTag(tag)"
        >
          <SvgIcon
            type="mdi"
            :path="mdiTagOutline"
            size="1em"
            class="mr-2 shrink-0 text-theme-text-very-muted"
          />
          <span class="truncate">#{{ tag }}</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { mdiChevronDown, mdiChevronLeft, mdiChevronRight, mdiFileDocumentOutline, mdiTagOutline } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";

import { getNotes, getTags } from "../api.js";
import { params, searchSortOptions } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";

const router = useRouter();
const route = useRoute();
const globalStore = useGlobalStore();
const filterText = ref("");
const tags = ref([]);
const tagsExpanded = ref(false);

const visible = computed(() => globalStore.sidebarVisible);

const filteredNotes = computed(() => {
  if (!filterText.value) return globalStore.notesList;
  const term = filterText.value.toLowerCase();
  return globalStore.notesList.filter((n) =>
    n.title.toLowerCase().includes(term),
  );
});

function isActive(title) {
  return title === globalStore.currentNoteTitle;
}

function openNote(title) {
  router.push({ name: "note", params: { title } });
}

function searchTag(tag) {
  router.push({
    name: "search",
    query: { [params.searchTerm]: `#${tag}`, [params.sortBy]: String(searchSortOptions.title) },
  });
}

function toggleSidebar() {
  globalStore.toggleSidebar();
}

async function fetchNotes() {
  try {
    const notes = await getNotes("*", "title", "asc", 1000);
    globalStore.notesList = notes;
  } catch (error) {
    console.error("Failed to fetch notes for sidebar:", error);
  }
}

async function fetchTags() {
  try {
    tags.value = await getTags();
  } catch (error) {
    console.error("Failed to fetch tags:", error);
  }
}

watch(() => route.fullPath, () => {
  fetchNotes();
  fetchTags();
});
onMounted(() => {
  fetchNotes();
  fetchTags();
});
</script>
