#!/usr/bin/env node

/**
 * Screenshot Capture Script for OMARINO EMS Suite
 * 
 * This script uses Puppeteer to capture screenshots of the webapp.
 * 
 * Usage:
 *   npm install -g puppeteer
 *   node scripts/capture-screenshots.js
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const BASE_URL = 'http://localhost:3000';
const SCREENSHOTS_DIR = path.join(__dirname, '..', 'docs', 'screenshots');

const pages = [
  { name: 'home', path: '/', title: 'Home Dashboard' },
  { name: 'dashboard', path: '/dashboard', title: 'Analytics Dashboard' },
  { name: 'timeseries', path: '/timeseries', title: 'Time Series Data' },
  { name: 'forecasts', path: '/forecasts', title: 'Forecasting' },
  { name: 'optimization', path: '/optimization', title: 'Optimization' },
  { name: 'scheduler', path: '/scheduler', title: 'Workflow Scheduler' }
];

async function captureScreenshots() {
  console.log('🚀 Starting screenshot capture...\n');

  // Launch browser
  const browser = await puppeteer.launch({
    headless: 'new',
    defaultViewport: {
      width: 1920,
      height: 1080,
      deviceScaleFactor: 1
    }
  });

  const page = await browser.newPage();

  // Create screenshots directory if it doesn't exist
  if (!fs.existsSync(SCREENSHOTS_DIR)) {
    fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
  }

  for (const pageInfo of pages) {
    try {
      console.log(`📸 Capturing: ${pageInfo.title} (${pageInfo.path})`);
      
      await page.goto(`${BASE_URL}${pageInfo.path}`, {
        waitUntil: 'networkidle2',
        timeout: 10000
      });

      // Wait a bit for any animations to complete
      await page.waitForTimeout(1000);

      const screenshotPath = path.join(SCREENSHOTS_DIR, `${pageInfo.name}.png`);
      await page.screenshot({
        path: screenshotPath,
        fullPage: false
      });

      console.log(`   ✅ Saved: ${screenshotPath}\n`);
    } catch (error) {
      console.error(`   ❌ Failed to capture ${pageInfo.title}: ${error.message}\n`);
    }
  }

  await browser.close();

  console.log('✨ Screenshot capture complete!');
  console.log(`📁 Screenshots saved to: ${SCREENSHOTS_DIR}`);
}

captureScreenshots().catch(console.error);
