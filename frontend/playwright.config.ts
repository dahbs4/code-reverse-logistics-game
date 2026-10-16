import { defineConfig } from '@playwright/test'
export default defineConfig({testDir:'./tests',timeout:180000,use:{launchOptions:{executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']},baseURL:'http://127.0.0.1:5173',viewport:{width:1440,height:1000},screenshot:'only-on-failure',trace:'retain-on-failure'},workers:1})
