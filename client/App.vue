<template>
  <div class="flex h-screen flex-col">
    <PrimeToast />
    <SearchModal v-model="isSearchModalVisible" />

    <template v-if="route.name === 'login'">
      <LoadingIndicator ref="loadingIndicator" class="container mx-auto flex h-screen flex-col px-2 py-4">
        <RouterView />
      </LoadingIndicator>
    </template>

    <template v-else>
      <!-- Top Bar -->
      <header class="flex items-center justify-between border-b border-theme-border bg-theme-background px-3 py-1.5">
        <div class="flex items-center gap-2">
          <button
            class="rounded p-1 text-theme-text-muted hover:bg-theme-background-elevated"
            @click="toggleSidebar"
            title="Toggle sidebar"
          >
            <SvgIcon type="mdi" :path="mdiMenu" size="1.25em" />
          </button>
          <RouterLink :to="{ name: 'home' }" class="text-sm font-semibold text-theme-text hover:text-theme-brand">
            Selfnotes
          </RouterLink>
        </div>

        <div class="flex items-center gap-1">
          <button
            class="rounded px-2 py-1 text-sm text-theme-text-muted hover:bg-theme-background-elevated"
            @click="toggleSearchModal"
            title="Search (/)"
          >
            <SvgIcon type="mdi" :path="mdiMagnify" size="1.25em" />
            <span class="ml-1 hidden md:inline">Search</span>
          </button>
          <RouterLink
            v-if="canCreate"
            :to="{ name: 'new' }"
            class="rounded px-2 py-1 text-sm text-theme-text-muted hover:bg-theme-background-elevated"
            title="New note (Ctrl+Alt+N)"
          >
            <SvgIcon type="mdi" :path="mdiPlus" size="1.25em" />
            <span class="ml-1 hidden md:inline">New Note</span>
          </RouterLink>
          <button
            class="rounded px-2 py-1 text-sm text-theme-text-muted hover:bg-theme-background-elevated"
            @click="toggleTheme"
            title="Toggle theme"
          >
            <SvgIcon type="mdi" :path="mdiThemeLightDark" size="1.25em" />
          </button>
          <button
            v-if="showLogOut"
            class="rounded px-2 py-1 text-sm text-theme-text-muted hover:bg-theme-background-elevated"
            @click="logOut"
            title="Log out"
          >
            <SvgIcon type="mdi" :path="mdiLogout" size="1.25em" />
          </button>
        </div>
      </header>

      <!-- Body -->
      <div class="flex flex-1 overflow-hidden">
        <FileExplorer />
        <main class="flex-1 overflow-y-auto">
          <LoadingIndicator ref="loadingIndicator" class="container mx-auto flex h-full flex-col px-4 py-4 print:max-w-full">
            <RouterView />
          </LoadingIndicator>
        </main>
      </div>
    </template>
  </div>
</template>

<script setup>
import { mdiLogout, mdiMagnify, mdiMenu, mdiPlus, mdiThemeLightDark } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";
import Mousetrap from "mousetrap";
import "mousetrap/plugins/global-bind/mousetrap-global-bind";
import { useToast } from "primevue/usetoast";
import { computed, ref } from "vue";
import { RouterView, useRoute } from "vue-router";

import { apiErrorHandler, getConfig } from "./api.js";
import FileExplorer from "./components/FileExplorer.vue";
import PrimeToast from "./components/PrimeToast.vue";
import { authTypes } from "./constants.js";
import { useGlobalStore } from "./globalStore.js";
import { loadTheme, toggleTheme } from "./helpers.js";
import { clearStoredToken } from "./tokenStorage.js";
import SearchModal from "./partials/SearchModal.vue";
import LoadingIndicator from "./components/LoadingIndicator.vue";
import router from "./router.js";

const globalStore = useGlobalStore();
const isSearchModalVisible = ref(false);
const loadingIndicator = ref();
const route = useRoute();
const toast = useToast();

const canCreate = computed(() => globalStore.config.authType !== authTypes.readOnly);
const showLogOut = computed(() => ![authTypes.none, authTypes.readOnly].includes(globalStore.config.authType));

Mousetrap.bind("/", () => {
  if (route.name !== "login") {
    toggleSearchModal();
    return false;
  }
});

Mousetrap.bindGlobal("ctrl+alt+n", () => {
  if (route.name !== "login") {
    router.push({ name: "new" });
    return false;
  }
});

Mousetrap.bindGlobal("ctrl+alt+h", () => {
  if (route.name !== "login") {
    router.push({ name: "home" });
    return false;
  }
});

Mousetrap.bindGlobal("ctrl+\\", () => {
  if (route.name !== "login") {
    globalStore.toggleSidebar();
    return false;
  }
});

getConfig()
  .then((data) => {
    globalStore.config = data;
    loadingIndicator.value.setLoaded();
  })
  .catch((error) => {
    apiErrorHandler(error, toast);
    loadingIndicator.value.setFailed();
  });

function toggleSearchModal() {
  isSearchModalVisible.value = !isSearchModalVisible.value;
}

function toggleSidebar() {
  globalStore.toggleSidebar();
}

function logOut() {
  clearStoredToken();
  localStorage.clear();
  router.push({ name: "login" });
}

loadTheme();
</script>
