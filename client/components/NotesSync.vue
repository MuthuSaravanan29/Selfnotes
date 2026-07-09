<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-50 flex items-start justify-center bg-slate-950/40 pt-[15vh] backdrop-blur-sm"
    @click.self="close"
  >
    <div class="mx-2 w-full max-w-[520px] rounded-lg border border-theme-border bg-theme-background shadow-2xl">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-theme-border px-5 py-4">
        <h2 class="text-lg font-semibold text-theme-text">Notes Sync</h2>
        <button class="text-theme-text-muted hover:text-theme-text" @click="close">&times;</button>
      </div>

      <!-- Step 1: Remote URL -->
      <div v-if="step === 1" class="px-5 py-4">
        <p class="mb-3 text-sm text-theme-text-muted">Enter your Git repository URL to sync notes.</p>
        <label class="mb-1 block text-xs font-semibold text-theme-text-muted">Repository URL</label>
        <input
          v-model="remoteUrl"
          type="text"
          placeholder="https://github.com/user/repo.git"
          class="mb-4 w-full rounded border border-theme-border bg-theme-background-elevated px-3 py-2 text-sm text-theme-text outline-none focus:border-theme-brand"
        />
        <div class="flex justify-end gap-2">
          <button class="rounded px-4 py-2 text-sm text-theme-text-muted hover:bg-theme-background-elevated" @click="close">Cancel</button>
          <button
            class="rounded bg-theme-brand px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-50"
            :disabled="!remoteUrl.trim()"
            @click="step = 2"
          >Next</button>
        </div>
      </div>

      <!-- Step 2: Auth Method -->
      <div v-if="step === 2" class="px-5 py-4">
        <p class="mb-3 text-sm text-theme-text-muted">Choose how to authenticate with the repository.</p>

        <!-- Auth Method Toggle -->
        <div class="mb-4 flex rounded-lg border border-theme-border p-1">
          <button
            class="flex-1 rounded-md px-3 py-2 text-sm font-medium"
            :class="authType === 'token' ? 'bg-theme-brand text-white' : 'text-theme-text-muted hover:bg-theme-background-elevated'"
            @click="authType = 'token'"
          >Token</button>
          <button
            class="flex-1 rounded-md px-3 py-2 text-sm font-medium"
            :class="authType === 'ssh' ? 'bg-theme-brand text-white' : 'text-theme-text-muted hover:bg-theme-background-elevated'"
            @click="authType = 'ssh'"
          >SSH Key</button>
        </div>

        <!-- Token Auth -->
        <div v-if="authType === 'token'">
          <label class="mb-1 block text-xs font-semibold text-theme-text-muted">Personal Access Token</label>
          <input
            v-model="token"
            type="password"
            placeholder="ghp_..."
            class="mb-3 w-full rounded border border-theme-border bg-theme-background-elevated px-3 py-2 text-sm text-theme-text outline-none focus:border-theme-brand"
          />
          <p class="mb-4 text-xs text-theme-text-very-muted">
            Create a token at GitHub → Settings → Developer settings → Personal access tokens with <code>repo</code> scope.
          </p>
        </div>

        <!-- SSH Auth -->
        <div v-if="authType === 'ssh'">
          <div class="mb-3 rounded-lg border border-theme-border bg-theme-background-elevated p-3 text-sm text-theme-text-muted">
            <p class="mb-2 font-semibold text-theme-text">SSH Private Key</p>
            <p class="mb-2">Paste your <strong>private</strong> key below (e.g. contents of <code class="rounded bg-theme-background px-1">~/.ssh/id_ed25519</code>):</p>
            <textarea
              v-model="sshKey"
              rows="6"
              placeholder="-----BEGIN OPENSSH PRIVATE KEY-----&#10;...&#10;-----END OPENSSH PRIVATE KEY-----"
              class="mb-3 w-full rounded border border-theme-border bg-theme-background-elevated px-3 py-2 text-sm text-theme-text outline-none focus:border-theme-brand font-mono"
            ></textarea>
            <p class="mb-2 font-semibold text-theme-text">Steps to add your public key to GitHub:</p>
            <ol class="list-inside list-decimal space-y-1">
              <li>Go to GitHub → Settings → SSH and GPG keys → New SSH key</li>
              <li>Paste your <strong>public</strong> key (<code class="rounded bg-theme-background px-1">cat ~/.ssh/id_ed25519.pub</code>) and save</li>
            </ol>
          </div>
        </div>

        <div class="flex justify-end gap-2">
          <button class="rounded px-4 py-2 text-sm text-theme-text-muted hover:bg-theme-background-elevated" @click="step = 1">Back</button>
          <button
            class="rounded bg-theme-brand px-4 py-2 text-sm text-white hover:opacity-90 disabled:opacity-50"
            :disabled="authType === 'token' && !token.trim()"
            @click="saveAndVerify"
          >{{ authType === 'token' ? 'Verify & Save' : 'Done' }}</button>
        </div>
      </div>

      <!-- Step 3: Verifying -->
      <div v-if="step === 3" class="px-5 py-8 text-center">
        <div v-if="verifying" class="flex flex-col items-center">
          <div class="loader mb-4"></div>
          <p class="text-sm text-theme-text-muted">Verifying sync connection...</p>
        </div>
        <div v-else-if="verifyResult === 'success'" class="flex flex-col items-center">
          <div class="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-green-100 text-green-600">
            <SvgIcon type="mdi" :path="mdiCheck" size="1.5em" />
          </div>
          <p class="mb-1 text-sm font-semibold text-theme-text">Sync Verified!</p>
          <p class="mb-4 text-sm text-theme-text-muted">{{ verifyMessage }}</p>
          <button class="rounded bg-theme-brand px-4 py-2 text-sm text-white hover:opacity-90" @click="close">Done</button>
        </div>
        <div v-else-if="verifyResult === 'error'" class="flex flex-col items-center">
          <div class="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600">
            <SvgIcon type="mdi" :path="mdiClose" size="1.5em" />
          </div>
          <p class="mb-1 text-sm font-semibold text-theme-text">Verification Failed</p>
          <p class="mb-4 max-w-sm text-sm text-theme-text-muted">{{ verifyMessage }}</p>
          <div class="flex gap-2">
            <button class="rounded px-4 py-2 text-sm text-theme-text-muted hover:bg-theme-background-elevated" @click="close">Close</button>
            <button class="rounded bg-theme-brand px-4 py-2 text-sm text-white hover:opacity-90" @click="step = 2">Retry</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.loader,
.loader:before,
.loader:after {
  background: rgb(var(--theme-brand));
  animation: load1 1s infinite ease-in-out;
  width: 1em;
  height: 4em;
}
.loader {
  color: rgb(var(--theme-brand));
  text-indent: -9999em;
  position: relative;
  font-size: 11px;
  animation-delay: -0.16s;
}
.loader:before,
.loader:after {
  position: absolute;
  top: 0;
  content: "";
}
.loader:before {
  left: -1.5em;
  animation-delay: -0.32s;
}
.loader:after {
  left: 1.5em;
}
@keyframes load1 {
  0%, 80%, 100% { box-shadow: 0 0; height: 4em; }
  40% { box-shadow: 0 -2em; height: 5em; }
}
code {
  font-size: 0.85em;
}
</style>

<script setup>
import { mdiCheck, mdiClose } from "@mdi/js";
import SvgIcon from "@jamescoyle/vue-icon";
import { ref } from "vue";

import { setGitConfig, verifyGitSync } from "../api.js";
import { useToast } from "primevue/usetoast";
import { getToastOptions } from "../helpers.js";

const props = defineProps({ visible: Boolean });
const emit = defineEmits(["close"]);

const toast = useToast();
const step = ref(1);
const remoteUrl = ref("");
const authType = ref("token");
const token = ref("");
const sshKey = ref("");
const verifying = ref(false);
const verifyResult = ref(null);
const verifyMessage = ref("");

async function saveAndVerify() {
  try {
    await setGitConfig(remoteUrl.value.trim(), authType.value, token.value.trim(), sshKey.value.trim());
  } catch (error) {
    toast.add(getToastOptions("Failed to save configuration.", "Error", "error"));
    return;
  }

  step.value = 3;
  verifying.value = true;
  verifyResult.value = null;
  verifyMessage.value = "";

  try {
    const result = await verifyGitSync();
    verifying.value = false;
    if (result.status === "success") {
      verifyResult.value = "success";
      verifyMessage.value = result.message || "Notes will now sync automatically on every change.";
    } else {
      verifyResult.value = "error";
      verifyMessage.value = result.message || "Could not connect to the repository. Check your URL and credentials.";
    }
  } catch (error) {
    verifying.value = false;
    verifyResult.value = "error";
    verifyMessage.value = error.response?.data?.detail || error.message || "Connection failed";
  }
}

function close() {
  step.value = 1;
  remoteUrl.value = "";
  authType.value = "token";
  token.value = "";
  sshKey.value = "";
  verifying.value = false;
  verifyResult.value = null;
  verifyMessage.value = "";
  emit("close");
}
</script>
