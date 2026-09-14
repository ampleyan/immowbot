<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const emit = defineEmits(['authenticated'])
const username = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)
const trusted = ref(false)

onMounted(async () => {
  try {
    const result = await api.checkTrusted()
    trusted.value = result.trusted
  } catch {}
})

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    await api.login(username.value, password.value)
    emit('authenticated')
  } catch {
    error.value = 'Invalid username or password'
  } finally {
    submitting.value = false
  }
}

async function quickAccess() {
  submitting.value = true
  error.value = ''
  try {
    await api.loginTrusted()
    emit('authenticated')
  } catch {
    error.value = 'Quick access failed'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <div class="login-card">
      <div class="sidebar-title">MAKELAARTJE</div>
      <p class="login-subtitle">Sign in to your property dashboard</p>

      <button v-if="trusted" class="btn btn-primary login-quick-access" type="button" :disabled="submitting" @click="quickAccess">
        {{ submitting ? 'Signing in…' : 'Continue as ampleyan' }}
      </button>

      <div v-if="trusted" class="login-divider"><span>or sign in with password</span></div>

      <form @submit.prevent="submit">
        <label for="login-user">Username</label>
        <input id="login-user" v-model="username" autocomplete="username" required />
        <label for="login-password">Password</label>
        <input id="login-password" v-model="password" type="password" autocomplete="current-password" required />
        <p v-if="error" class="login-error">{{ error }}</p>
        <button class="btn btn-primary" type="submit" :disabled="submitting">{{ submitting ? 'Signing in…' : 'Sign in' }}</button>
      </form>
    </div>
  </main>
</template>
