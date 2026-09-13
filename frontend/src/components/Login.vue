<script setup>
import { ref } from 'vue'
import { api } from '../api.js'

const emit = defineEmits(['authenticated'])
const username = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

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
</script>

<template>
  <main class="login-page">
    <form class="login-card" @submit.prevent="submit">
      <div class="sidebar-title">Immowbot</div>
      <p class="login-subtitle">Sign in to your property dashboard</p>
      <label for="login-user">Username</label>
      <input id="login-user" v-model="username" autocomplete="username" required />
      <label for="login-password">Password</label>
      <input id="login-password" v-model="password" type="password" autocomplete="current-password" required />
      <p v-if="error" class="login-error">{{ error }}</p>
      <button class="btn btn-primary" type="submit" :disabled="submitting">{{ submitting ? 'Signing in…' : 'Sign in' }}</button>
    </form>
  </main>
</template>
