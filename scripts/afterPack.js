const fs = require('fs-extra');
const path = require('path');

module.exports = async function(context) {
  const buildPath = path.join(context.appOutDir, 'resources', 'app');
  
  // Remove any remaining Python executables
  const exeFiles = [
    path.join(buildPath, 'django-backend', '**', '*.exe'),
    path.join(buildPath, 'django-backend', '**', '*.dll')
  ];
  
  for (const pattern of exeFiles) {
    const files = await fs.glob(pattern);
    for (const file of files) {
      await fs.remove(file);
    }
  }
};