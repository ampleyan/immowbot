<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api.js'

const props = defineProps({ token: { type: String, required: true } })
const emit = defineEmits(['authenticated'])

const valid = ref(null)
const username = ref('')
const password = ref('')
const confirm = ref('')
const error = ref('')
const submitting = ref(false)

onMounted(async () => {
  try {
    await api.checkInvite(props.token)
    valid.value = true
  } catch {
    valid.value = false
  }
})

async function submit() {
  if (password.value !== confirm.value) {
    error.value = 'Passwords do not match'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    await api.register(props.token, username.value, password.value)
    emit('authenticated')
    history.replaceState(null, '', '/')
  } catch (e) {
    error.value = e.message || 'Registration failed'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <div class="login-card">
      <div class="sidebar-title">MAKELAARTJE</div>

      <div v-if="valid === null" class="login-subtitle">Checking invite link…</div>

      <div v-else-if="valid === false">
        <p class="login-subtitle" style="color:#C01048">This invite link is invalid or has been disabled.</p>
      </div>

      <form v-else @submit.prevent="submit">
        <p class="login-subtitle">Create your account</p>
        <label for="reg-user">Username</label>
        <input id="reg-user" v-model="username" autocomplete="username" required minlength="3" />
        <label for="reg-pw">Password</label>
        <input id="reg-pw" v-model="password" type="password" autocomplete="new-password" required minlength="8" />
        <label for="reg-pw2">Confirm password</label>
        <input id="reg-pw2" v-model="confirm" type="password" autocomplete="new-password" required minlength="8" />
        <p v-if="error" class="login-error">{{ error }}</p>
        <button class="btn btn-primary" type="submit" :disabled="submitting" style="width:100%;margin-top:1.25rem">
          {{ submitting ? 'Creating account…' : 'Create account' }}
        </button>
      </form>
    </div>
  </main>
</template>
