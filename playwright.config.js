import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'ui/tests',use:{headless:true,channel:"chrome"},webServer:{command:'.venv/bin/python -m uvicorn ui.test_server:app --host 127.0.0.1 --port 8779',url:'http://127.0.0.1:8779/health',reuseExistingServer:false},workers:1});
