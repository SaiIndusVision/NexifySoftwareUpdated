// const { app, BrowserWindow, shell } = require('electron');
// const path = require('path');
// const { spawn, exec } = require('child_process');
// const fs = require('fs');
// const os = require('os');

// let mainWindow;
// let djangoProcess;

// const isDev = process.argv.includes('--dev');

// function createWindow() {
//     mainWindow = new BrowserWindow({
//         width: 1200,
//         height: 800,
//         webPreferences: {
//             nodeIntegration: false,
//             contextIsolation: true,
//             enableRemoteModule: false,
//         },
//         icon: path.join(__dirname, '..', 'assets', 'icon.png'),
//         show: false
//     });

//     mainWindow.loadFile(path.join(__dirname, 'loading.html'));
//     mainWindow.show();

//     startDjangoServer().then(() => {
//         setTimeout(() => {
//             mainWindow.loadURL('http://localhost:8000');
//         }, 3000);
//     }).catch(error => {
//         console.error('Failed to start Django:', error);
//         mainWindow.loadFile(path.join(__dirname, 'error.html'));
//     });

//     mainWindow.on('closed', () => {
//         mainWindow = null;
//         stopDjangoServer();
//     });
// }

// function getDjangoPath() {
//     return isDev
//         ? path.join(__dirname, '..', 'django-backend')
//         : path.join(process.resourcesPath, 'django-backend');
// }

// function getPythonCommand(djangoPath) {
//     const platform = os.platform();
//     const venvPath = isDev
//         ? path.join(__dirname, '..', 'nexify_env') // Use nexify_env in development
//         : path.join(process.resourcesPath, 'nexify_env'); // Use nexify_env in production

//     if (platform === 'win32') {
//         const venvPython = path.join(venvPath, 'Scripts', 'python.exe');
//         if (fs.existsSync(venvPython)) return venvPython;
//     } else {
//         const venvPython = path.join(venvPath, 'bin', 'python');
//         if (fs.existsSync(venvPython)) return venvPython;
//     }

//     return platform === 'win32' ? 'python' : 'python3';
// }

// async function installRequirements(djangoPath) {
//     const pythonCmd = getPythonCommand(djangoPath);
//     const requirementsPath = path.join(djangoPath, 'requirements.txt');

//     if (!fs.existsSync(requirementsPath)) {
//         console.log('No requirements.txt found. Skipping installation.');
//         return;
//     }

//     return new Promise((resolve) => {
//         const pipProcess = spawn(pythonCmd, ['-m', 'pip', 'install', '-r', 'requirements.txt'], {
//             cwd: djangoPath,
//             stdio: ['pipe', 'pipe', 'pipe']
//         });

//         pipProcess.stdout.on('data', data => console.log('Pip stdout:', data.toString()));
//         pipProcess.stderr.on('data', data => console.log('Pip stderr:', data.toString()));

//         pipProcess.on('close', code => {
//             console.log(code === 0 ? 'Requirements installed' : 'Pip failed, continuing...');
//             resolve();
//         });

//         pipProcess.on('error', error => {
//             console.log('Pip install error:', error.message);
//             resolve();
//         });
//     });
// }

// async function startDjangoServer() {
//     const djangoPath = getDjangoPath();
//     console.log('Django path:', djangoPath);

//     if (!fs.existsSync(djangoPath)) throw new Error(`Django backend not found at: ${djangoPath}`);
//     if (!fs.existsSync(path.join(djangoPath, 'manage.py'))) throw new Error('manage.py not found');

//     await installRequirements(djangoPath);

//     const pythonCmd = getPythonCommand(djangoPath);
//     console.log('Starting Django with:', pythonCmd);

//     return new Promise((resolve, reject) => {
//         djangoProcess = spawn(pythonCmd, ['manage.py', 'runserver', '8000'], {
//             cwd: djangoPath,
//             stdio: ['pipe', 'pipe', 'pipe']
//         });

//         let serverStarted = false;

//         const tryResolve = () => {
//             if (!serverStarted) {
//                 serverStarted = true;
//                 resolve();
//             }
//         };

//         djangoProcess.stdout.on('data', data => {
//             const output = data.toString();
//             console.log('Django stdout:', output);
//             if (output.includes('Starting development server') || output.includes('Django version')) {
//                 tryResolve();
//             }
//         });

//         djangoProcess.stderr.on('data', data => {
//             const error = data.toString();
//             console.log('Django stderr:', error);
//             if (error.includes('Starting development server') || error.includes('file changes')) {
//                 tryResolve();
//             }
//         });

//         djangoProcess.on('close', code => {
//             console.log(`Django process exited with code ${code}`);
//             if (!serverStarted) reject(new Error(`Django failed to start: ${code}`));
//         });

//         djangoProcess.on('error', error => {
//             console.error('Error starting Django:', error);
//             if (!serverStarted) reject(error);
//         });

//         // Timeout fallback
//         setTimeout(() => {
//             if (!serverStarted) {
//                 console.log('Timeout: assuming Django started.');
//                 tryResolve();
//             }
//         }, 10000);
//     });
// }

// function stopDjangoServer() {
//     if (djangoProcess && !djangoProcess.killed) {
//         console.log('Killing Django process...');
//         djangoProcess.kill('SIGKILL');
//     }

//     const killCommand = process.platform === 'win32'
//         ? 'for /f "tokens=5" %a in (\'netstat -nao ^| find ":8000"\') do taskkill /F /PID %a'
//         : 'lsof -ti:8000 | xargs -r kill -9';

//     exec(killCommand, (err, stdout, stderr) => {
//         if (err) {
//             console.error('Failed to free port 8000:', err.message);
//         } else {
//             console.log('✅ Freed up port 8000.');
//         }
//     });
// }

// app.whenReady().then(createWindow);

// app.on('window-all-closed', () => {
//     stopDjangoServer();
//     if (process.platform !== 'darwin') app.quit();
// });

// app.on('activate', () => {
//     if (BrowserWindow.getAllWindows().length === 0) createWindow();
// });

// app.on('web-contents-created', (event, contents) => {
//     contents.on('new-window', (event, navigationUrl) => {
//         event.preventDefault();
//         shell.openExternal(navigationUrl);
//     });
// });


const { app, BrowserWindow, shell, dialog } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');
const fs = require('fs');
const os = require('os');

let mainWindow;
let djangoProcess;

const isDev = process.argv.includes('--dev');

// ----------------------
// Minimal tamper control
// ----------------------
function getTamperStatePath() {
    try {
        return path.join(app.getPath('userData'), 'tamper.json');
    } catch (e) {
        // Fallback to temp if userData isn't available yet
        return path.join(os.tmpdir(), 'nexify_tamper.json');
    }
}

function loadTamperState() {
    const statePath = getTamperStatePath();
    try {
        const raw = fs.readFileSync(statePath, 'utf8');
        return JSON.parse(raw);
    } catch (e) {
        return { warnedOnce: false, deletedOnce: false };
    }
}

function saveTamperState(state) {
    const statePath = getTamperStatePath();
    try {
        fs.mkdirSync(path.dirname(statePath), { recursive: true });
        fs.writeFileSync(statePath, JSON.stringify(state));
    } catch (e) {
        // ignore
    }
}

function detectTamper() {
    try {
        // Consider these as tamper in production
        if (!isDev && !app.isPackaged) return true; // running unpacked build
        if (!isDev && !__dirname.includes('app.asar')) return true; // asar unpacked
        if (process.env.NODE_OPTIONS && /--inspect|--require/.test(process.env.NODE_OPTIONS)) return true;
        if (process.execArgv && process.execArgv.some(a => /--inspect|--remote-debugging-port/.test(a))) return true;
        if (process.env.ELECTRON_RUN_AS_NODE) return true;
        return false;
    } catch (e) {
        return false;
    }
}

function deleteSensitiveFiles() {
    const toDelete = [];
    try {
        // Backend resources inside packaged app
        toDelete.push(path.join(process.resourcesPath || '', 'django-backend'));
        toDelete.push(path.join(process.resourcesPath || '', 'nexify_env'));
    } catch (e) {}
    try {
        // User data cache/state
        toDelete.push(app.getPath('userData'));
    } catch (e) {}

    for (const target of toDelete) {
        try {
            if (target && fs.existsSync(target)) {
                fs.rmSync(target, { recursive: true, force: true });
            }
        } catch (e) {
            // continue
        }
    }
}

async function handleTamperAndExit() {
    const state = loadTamperState();
    if (state.warnedOnce && !state.deletedOnce) {
        try {
            dialog.showErrorBox('Security violation', 'Repeated tampering detected. Sensitive files will be removed and the app will close.');
        } catch (e) {}
        deleteSensitiveFiles();
        state.deletedOnce = true;
        saveTamperState(state);
        try { stopDjangoServer(); } catch (e) {}
        app.quit();
        return true;
    }

    if (!state.warnedOnce) {
        state.warnedOnce = true;
        saveTamperState(state);
        try {
            dialog.showMessageBoxSync({
                type: 'warning',
                buttons: ['OK'],
                title: 'Warning',
                message: 'Tamper attempt detected. Further attempts will lock and remove app data.'
            });
        } catch (e) {}
        try { stopDjangoServer(); } catch (e) {}
        app.quit();
        return true;
    }

    return false;
}

// Watch resources for changes while the app is running (cannot detect mere "opens")
let resourceWatchers = [];
function startResourceWatchers() {
    if (isDev) return;
    try {
        const watchTargets = [];
        if (process.resourcesPath) watchTargets.push(process.resourcesPath);
        try { watchTargets.push(path.join(process.resourcesPath || '', 'django-backend')); } catch (e) {}
        try { watchTargets.push(path.join(process.resourcesPath || '', 'nexify_env')); } catch (e) {}

        const onChange = async () => {
            // Debounce by closing further events temporarily
            for (const w of resourceWatchers) { try { w.close(); } catch (e) {} }
            resourceWatchers = [];
            await handleTamperAndExit();
        };

        for (const target of watchTargets) {
            if (!target || !fs.existsSync(target)) continue;
            try {
                const watcher = fs.watch(target, { recursive: true }, (eventType, filename) => {
                    // Only react to actual file system changes
                    if (eventType === 'change' || eventType === 'rename') {
                        onChange();
                    }
                });
                resourceWatchers.push(watcher);
            } catch (e) {
                // ignore watcher errors for non-supported platforms
            }
        }
    } catch (e) {
        // ignore
    }
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            enableRemoteModule: false,
        },
        icon: path.join(__dirname, '..', 'assets', 'icon.png'),
        show: false
    });

    mainWindow.loadFile(path.join(__dirname, 'loading.html'));
    mainWindow.show();

    startDjangoServer().then(() => {
        setTimeout(() => {
            mainWindow.loadURL('http://localhost:8000');
        }, 3000);
    }).catch(error => {
        console.error('Failed to start Django:', error);
        mainWindow.loadFile(path.join(__dirname, 'error.html'));
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
        stopDjangoServer();
    });
}

function getDjangoPath() {
    return isDev
        ? path.join(__dirname, '..', 'django-backend')
        : path.join(process.resourcesPath, 'django-backend');
}

function getCompiledBackendPath() {
    try {
        return isDev
            ? path.join(__dirname, '..', 'backend_build', process.platform === 'win32' ? 'nexify_backend.exe' : 'nexify_backend')
            : path.join(process.resourcesPath, 'backend', process.platform === 'win32' ? 'nexify_backend.exe' : 'nexify_backend');
    } catch (e) {
        return null;
    }
}

async function createVirtualEnv(djangoPath) {
    const platform = os.platform();
    const venvPath = isDev
        ? path.join(__dirname, '..', 'nexify_env')
        : path.join(process.resourcesPath, 'nexify_env');
    const pythonCmd = platform === 'win32' ? 'python' : 'python3';

    if (fs.existsSync(venvPath)) {
        console.log(`Virtual environment already exists at: ${venvPath}`);
        return;
    }

    console.log(`Creating virtual environment at: ${venvPath}`);

    return new Promise((resolve, reject) => {
        const venvProcess = spawn(pythonCmd, ['-m', 'venv', 'nexify_env'], {
            cwd: isDev ? path.join(__dirname, '..') : process.resourcesPath,
            stdio: ['pipe', 'pipe', 'pipe']
        });

        venvProcess.stdout.on('data', data => console.log('venv stdout:', data.toString()));
        venvProcess.stderr.on('data', data => console.log('venv stderr:', data.toString()));

        venvProcess.on('close', code => {
            if (code === 0) {
                console.log('Virtual environment created successfully.');
                resolve();
            } else {
                console.error('Failed to create virtual environment.');
                reject(new Error(`Virtual environment creation failed with code ${code}`));
            }
        });

        venvProcess.on('error', error => {
            console.error('Error creating virtual environment:', error.message);
            reject(error);
        });
    });
}

function getPythonCommand(djangoPath) {
    const platform = os.platform();
    const venvPath = isDev
        ? path.join(__dirname, '..', 'nexify_env')
        : path.join(process.resourcesPath, 'nexify_env');

    if (platform === 'win32') {
        const venvPython = path.join(venvPath, 'Scripts', 'python.exe');
        if (fs.existsSync(venvPython)) return venvPython;
    } else {
        const venvPython = path.join(venvPath, 'bin', 'python');
        if (fs.existsSync(venvPython)) return venvPython;
    }

    return platform === 'win32' ? 'python' : 'python3';
}

async function installRequirements(djangoPath) {
    const pythonCmd = getPythonCommand(djangoPath);
    const requirementsPath = path.join(djangoPath, 'requirements.txt');

    // Create virtual environment if it doesn't exist
    await createVirtualEnv(djangoPath);

    if (!fs.existsSync(requirementsPath)) {
        console.log('No requirements.txt found. Skipping installation.');
        return;
    }

    // Ensure pip is upgraded in the virtual environment
    await new Promise((resolve) => {
        const pipUpgradeProcess = spawn(pythonCmd, ['-m', 'pip', 'install', '--upgrade', 'pip'], {
            cwd: djangoPath,
            stdio: ['pipe', 'pipe', 'pipe']
        });

        pipUpgradeProcess.stdout.on('data', data => console.log('Pip upgrade stdout:', data.toString()));
        pipUpgradeProcess.stderr.on('data', data => console.log('Pip upgrade stderr:', data.toString()));

        pipUpgradeProcess.on('close', code => {
            console.log(code === 0 ? 'Pip upgraded successfully' : 'Pip upgrade failed, continuing...');
            resolve();
        });

        pipUpgradeProcess.on('error', error => {
            console.log('Pip upgrade error:', error.message);
            resolve();
        });
    });

    // Install requirements
    return new Promise((resolve) => {
        const pipProcess = spawn(pythonCmd, ['-m', 'pip', 'install', '-r', 'requirements.txt'], {
            cwd: djangoPath,
            stdio: ['pipe', 'pipe', 'pipe']
        });

        pipProcess.stdout.on('data', data => console.log('Pip stdout:', data.toString()));
        pipProcess.stderr.on('data', data => console.log('Pip stderr:', data.toString()));

        pipProcess.on('close', code => {
            console.log(code === 0 ? 'Requirements installed' : 'Pip failed, continuing...');
            resolve();
        });

        pipProcess.on('error', error => {
            console.log('Pip install error:', error.message);
            resolve();
        });
    });
}

async function startDjangoServer() {
    const compiledPath = getCompiledBackendPath();
    const hasCompiled = compiledPath && fs.existsSync(compiledPath);
    const djangoPath = getDjangoPath();
    console.log('Using compiled backend:', hasCompiled ? compiledPath : 'not found');

    if (!hasCompiled) {
        console.log('Falling back to Python sources');
        if (!fs.existsSync(djangoPath)) throw new Error(`Django backend not found at: ${djangoPath}`);
        if (!fs.existsSync(path.join(djangoPath, 'manage.py'))) throw new Error('manage.py not found');
        await installRequirements(djangoPath);
    }

    return new Promise((resolve, reject) => {
        if (hasCompiled) {
            const args = ['runserver', '127.0.0.1:8000'];
            djangoProcess = spawn(compiledPath, args, {
                cwd: path.dirname(compiledPath),
                stdio: ['pipe', 'pipe', 'pipe']
            });
        } else {
            const pythonCmd = getPythonCommand(djangoPath);
            console.log('Starting Django with:', pythonCmd);
            const env = { ...process.env };
            const buildPath = path.join(djangoPath, 'build');
            if (fs.existsSync(buildPath)) {
                env.PYTHONPATH = env.PYTHONPATH
                    ? `${buildPath}${path.delimiter}${env.PYTHONPATH}`
                    : buildPath;
                console.log('Using Cython build at:', buildPath);
            }
            djangoProcess = spawn(pythonCmd, ['manage.py', 'runserver', '8000'], {
                cwd: djangoPath,
                stdio: ['pipe', 'pipe', 'pipe'],
                env
            });
        }

        let serverStarted = false;

        const tryResolve = () => {
            if (!serverStarted) {
                serverStarted = true;
                resolve();
            }
        };

        djangoProcess.stdout.on('data', data => {
            const output = data.toString();
            console.log('Django stdout:', output);
            if (output.includes('Starting development server') || output.includes('Django version')) {
                tryResolve();
            }
        });

        djangoProcess.stderr.on('data', data => {
            const error = data.toString();
            console.log('Django stderr:', error);
            if (error.includes('Starting development server') || error.includes('file changes')) {
                tryResolve();
            }
        });

        djangoProcess.on('close', code => {
            console.log(`Django process exited with code ${code}`);
            if (!serverStarted) reject(new Error(`Django failed to start: ${code}`));
        });

        djangoProcess.on('error', error => {
            console.error('Error starting Django:', error);
            if (!serverStarted) reject(error);
        });

        // Timeout fallback
        setTimeout(() => {
            if (!serverStarted) {
                console.log('Timeout: assuming Django started.');
                tryResolve();
            }
        }, 10000);
    });
}

function stopDjangoServer() {
    if (djangoProcess && !djangoProcess.killed) {
        console.log('Killing Django process...');
        djangoProcess.kill('SIGKILL');
    }

    const killCommand = process.platform === 'win32'
        ? 'for /f "tokens=5" %a in (\'netstat -nao ^| find ":8000"\') do taskkill /F /PID %a'
        : 'lsof -ti:8000 | xargs -r kill -9';

    exec(killCommand, (err, stdout, stderr) => {
        if (err) {
            console.error('Failed to free port 8000:', err.message);
        } else {
            console.log('✅ Freed up port 8000.');
        }
    });
}

app.whenReady().then(async () => {
    if (!isDev && detectTamper()) {
        await handleTamperAndExit();
        return;
    }
    createWindow();
    startResourceWatchers();
});

app.on('window-all-closed', () => {
    stopDjangoServer();
    if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

app.on('web-contents-created', (event, contents) => {
    contents.on('new-window', (event, navigationUrl) => {
        event.preventDefault();
        shell.openExternal(navigationUrl);
    });
    // Block devtools in production and treat as tamper
    contents.on('devtools-opened', async () => {
        try { contents.closeDevTools(); } catch (e) {}
        if (!isDev) {
            await handleTamperAndExit();
        }
    });
    contents.on('context-menu', (e) => {
        if (!isDev) e.preventDefault();
    });
});