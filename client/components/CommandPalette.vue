<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/40 pt-[15vh] backdrop-blur-sm"
    @click.self="close"
  >
    <div class="mx-2 w-full max-w-[600px] overflow-hidden rounded-lg border border-theme-border bg-theme-background shadow-2xl">
      <div class="flex items-center border-b border-theme-border px-4 py-3">
        <SvgIcon type="mdi" :path="mdiMagnify" size="1.25em" class="mr-3 shrink-0 text-theme-text-muted" />
        <input
          ref="searchInput"
          v-model="query"
          type="text"
          class="w-full bg-transparent text-lg outline-none placeholder:text-theme-text-very-muted"
          placeholder="Type a command or note name..."
          @keydown="keydownHandler"
        />
      </div>

      <div class="max-h-[400px] overflow-y-auto">
        <!-- Commands Section -->
        <div v-if="filteredCommands.length > 0 || !query">
          <p class="px-4 pb-1 pt-3 text-xs font-semibold uppercase text-theme-text-very-muted">Commands</p>
          <div
            v-for="(cmd, idx) in filteredCommands"
            :key="'cmd-' + idx"
            class="flex cursor-pointer items-center px-4 py-2 text-sm"
            :class="selectedIndex === idx ? 'bg-theme-background-elevated' : 'hover:bg-theme-background-elevated'"
            @click="executeCommand(cmd)"
            @mousemove="selectedIndex = idx"
          >
            <SvgIcon
              type="mdi"
              :path="cmd.icon"
              size="1.25em"
              class="mr-3 shrink-0 text-theme-text-muted"
            />
            <span class="flex-1 text-theme-text">{{ cmd.label }}</span>
            <span v-if="cmd.shortcut" class="text-xs text-theme-text-very-muted">{{ cmd.shortcut }}</span>
          </div>
        </div>

        <!-- Notes Section -->
        <div v-if="filteredNotes.length > 0">
          <p class="border-t border-theme-border px-4 pb-1 pt-3 text-xs font-semibold uppercase text-theme-text-very-muted">
            Notes
          </p>
          <div
            v-for="(note, idx) in filteredNotes"
            :key="'note-' + idx"
            class="flex cursor-pointer items-center px-4 py-2 text-sm"
            :class="selectedIndex === filteredCommands.length + idx ? 'bg-theme-background-elevated' : 'hover:bg-theme-background-elevated'"
            @click="openNote(note.title)"
            @mousemove="selectedIndex = filteredCommands.length + idx"
          >
            <SvgIcon
              type="mdi"
              :path="mdiFileDocumentOutline"
              size="1.25em"
              class="mr-3 shrink-0 text-theme-text-muted"
            />
            <span class="text-theme-text">{{ note.title }}</span>
          </div>
        </div>

        <div v-if="filteredCommands.length === 0 && filteredNotes.length === 0 && query" class="px-4 py-8 text-center text-sm text-theme-text-very-muted">
          No results for "{{ query }}"
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { mdiCalendarToday, mdiFileDocumentOutline, mdiMagnify } from "@mdi/js";
import {
  mdilHome,
  mdilLogout,
  mdilMagnify as mdilMagnifyLight,
  mdilMonitor,
  mdilNoteMultiple,
  mdilPlusCircle,
} from "@mdi/light-js";
import SvgIcon from "@jamescoyle/vue-icon";
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import { params, searchSortOptions, authTypes } from "../constants.js";
import { useGlobalStore } from "../globalStore.js";
import { toggleTheme } from "../helpers.js";
import { clearStoredToken } from "../tokenStorage.js";
import { openDailyNote } from "../dailyNote.js";

const props = defineProps({ visible: Boolean });
const emit = defineEmits(["close"]);

const router = useRouter();
const globalStore = useGlobalStore();
const query = ref("");
const searchInput = ref();
const selectedIndex = ref(0);

const commands = computed(() => [
  { label: "Daily Note", icon: mdiCalendarToday, action: openDailyNote },
  { label: "New Note", icon: mdilPlusCircle, shortcut: "Ctrl+Alt+N", action: () => router.push({ name: "new" }) },
  { label: "Search Notes", icon: mdilMagnifyLight, shortcut: "/", action: () => emit("close") },
  { label: "All Notes", icon: mdilNoteMultiple, action: () => router.push({ name: "search", query: { [params.searchTerm]: "*", [params.sortBy]: String(searchSortOptions.title) } }) },
  { label: "Go to Home", icon: mdilHome, shortcut: "Ctrl+Alt+H", action: () => router.push({ name: "home" }) },
  { label: "Toggle Sidebar", icon: mdiFileDocumentOutline, shortcut: "Ctrl+\\", action: () => globalStore.toggleSidebar() },
  { label: "Toggle Theme", icon: mdilMonitor, action: toggleTheme },
  ...(globalStore.config.authType && ![authTypes.none, authTypes.readOnly].includes(globalStore.config.authType)
    ? [{ label: "Log Out", icon: mdilLogout, action: () => { clearStoredToken(); localStorage.clear(); router.push({ name: "login" }); } }]
    : []),
]);

const filteredCommands = computed(() => {
  if (!query.value) return commands.value;
  const q = query.value.toLowerCase();
  return commands.value.filter((c) => c.label.toLowerCase().includes(q));
});

const filteredNotes = computed(() => {
  if (!query.value) return globalStore.notesList;
  const q = query.value.toLowerCase();
  return globalStore.notesList.filter((n) => n.title.toLowerCase().includes(q));
});

const totalItems = computed(() => filteredCommands.value.length + filteredNotes.value.length);

function keydownHandler(event) {
  if (event.key === "ArrowDown") {
    event.preventDefault();
    selectedIndex.value = Math.min(selectedIndex.value + 1, totalItems.value - 1);
  } else if (event.key === "ArrowUp") {
    event.preventDefault();
    selectedIndex.value = Math.max(selectedIndex.value - 1, 0);
  } else if (event.key === "Enter") {
    event.preventDefault();
    executeSelected();
  } else if (event.key === "Escape") {
    close();
  }
}

function executeSelected() {
  const cmdCount = filteredCommands.value.length;
  if (selectedIndex.value < cmdCount) {
    filteredCommands.value[selectedIndex.value].action();
    close();
  } else {
    const noteIndex = selectedIndex.value - cmdCount;
    const note = filteredNotes.value[noteIndex];
    if (note) {
      openNote(note.title);
    }
  }
}

function executeCommand(cmd) {
  cmd.action();
  close();
}

function openNote(title) {
  globalStore.currentNoteTitle = title;
  router.push({ name: "note", params: { title } });
  close();
}

function close() {
  query.value = "";
  selectedIndex.value = 0;
  emit("close");
}

watch(
  () => props.visible,
  (v) => {
    if (v) nextTick(() => searchInput.value?.focus());
  },
);
</script>
