const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// Ensure Python environment is set up
try {
  // Create data directories
  const dirs = ['uploads', 'output', 'history', 'config'].map(dir => 
    path.join(process.cwd(), 'data', dir)
  );
  
  dirs.forEach(dir => {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  });

  // Install Python dependencies
  console.log('Installing Python dependencies...');
  execSync('pip install -r requirements.txt', { stdio: 'inherit' });
} catch (error) {
  console.error('Error during build:', error);
  process.exit(1);
}