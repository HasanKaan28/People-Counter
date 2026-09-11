using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Threading;
using System.Windows.Forms;

namespace PeopleCounter
{
    static class Program
    {
        private static Mutex appMutex = null;
        private static Process serverProcess = null;
        private static StreamWriter logWriter = null;
        private static readonly object logLock = new object();
        private static NotifyIcon trayIcon = null;
        private static string appUrl = "http://127.0.0.1:8000";
        private static string baseDir = "";

        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.SetUnhandledExceptionMode(UnhandledExceptionMode.CatchException);

            baseDir = AppDomain.CurrentDomain.BaseDirectory;

            // 1. Single-Instance Mutex: prevents duplicate instances & port conflicts
            bool createdNew = true;
            try
            {
                appMutex = new Mutex(true, "Local\\PeopleCounter_AI_Vision_App_Mutex_v1", out createdNew);
            }
            catch
            {
                createdNew = true;
            }

            if (!createdNew)
            {
                // App is already running in background! Just focus/launch the dedicated window
                LaunchAppWindow();
                return;
            }

            string venvPython = Path.Combine(baseDir, ".venv", "Scripts", "python.exe");
            string appPy = Path.Combine(baseDir, "app.py");

            string localAppDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "PeopleCounter");
            string localAppPy = Path.Combine(localAppDir, "app.py");
            string localAppExe = Path.Combine(localAppDir, "PeopleCounter.exe");
            string localVenvPython = Path.Combine(localAppDir, ".venv", "Scripts", "python.exe");

            // Check if app.py exists in baseDir
            if (!File.Exists(appPy))
            {
                if (File.Exists(localAppPy) && File.Exists(localAppExe))
                {
                    Process.Start(new ProcessStartInfo(localAppExe) { WorkingDirectory = localAppDir, UseShellExecute = true });
                    return;
                }

                string localSetup = Path.Combine(baseDir, "PeopleCounter-Setup.exe");
                if (File.Exists(localSetup))
                {
                    Process.Start(new ProcessStartInfo(localSetup, "/auto") { UseShellExecute = true });
                    return;
                }

                MessageBox.Show("AI Camera People Counter installation files were not found.\nPlease run 'PeopleCounter-Setup.exe' to complete installation.",
                                "Setup Required", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            // Check virtual environment (.venv)
            if (!File.Exists(venvPython))
            {
                if (File.Exists(localVenvPython))
                {
                    venvPython = localVenvPython;
                }
                else
                {
                    string setupExe = Path.Combine(baseDir, "PeopleCounter-Setup.exe");
                    if (File.Exists(setupExe))
                    {
                        Process p = Process.Start(new ProcessStartInfo(setupExe, "/auto") { UseShellExecute = true });
                        p.WaitForExit();
                    }
                    if (!File.Exists(venvPython))
                    {
                        MessageBox.Show("Python virtual environment (.venv) was not found. Please run PeopleCounter-Setup.exe to perform setup.",
                                        "Setup Incomplete", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        return;
                    }
                }
            }

            // Ensure verified Desktop Shortcuts with custom icon (asynchronous if already exists)
            EnsureDesktopShortcuts(Path.Combine(baseDir, "PeopleCounter.exe"), baseDir);

            // 2. Show Sleek Native Splash Screen
            using (SplashScreen splash = new SplashScreen())
            {
                splash.Show();
                Application.DoEvents();

                // Check if AI service is already running and healthy
                bool isAlive = IsServerResponding();
                if (!isAlive)
                {
                    splash.UpdateStatus("Cleaning up network ports...");
                    FreePort8000IfOccupied();

                    splash.UpdateStatus("Starting AI computer vision backend...");
                    StartBackgroundServer(venvPython, appPy, baseDir);

                    // Wait until server is responding at http://localhost:8000 with continuous message pump
                    bool isReady = WaitForServerReady(splash, 30);
                    if (!isReady)
                    {
                        splash.Close();
                        string errDetail = "";
                        try
                        {
                            string logPath = Path.Combine(baseDir, "server.log");
                            if (File.Exists(logPath))
                            {
                                string[] lines = File.ReadAllLines(logPath);
                                int startLine = Math.Max(0, lines.Length - 10);
                                errDetail = "\n\nLog detail:\n" + string.Join("\n", lines, startLine, lines.Length - startLine);
                            }
                        }
                        catch { }

                        MessageBox.Show("AI vision camera service failed to start." + errDetail,
                                        "Startup Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        StopBackgroundServer();
                        return;
                    }
                }

                splash.UpdateStatus("Launching application window...");
                Application.DoEvents();
                Thread.Sleep(150);
                splash.Close();
            }

            // 3. Open Dedicated Desktop App Window (No address bar, no tabs!)
            LaunchAppWindow();

            // 4. Setup System Tray Icon & Context Menu
            SetupSystemTray();

            // 5. Windows Message Loop (keeps running in System Tray until user exits)
            Application.Run();

            // Clean shutdown on exit
            StopBackgroundServer();
            if (trayIcon != null)
            {
                trayIcon.Visible = false;
                trayIcon.Dispose();
            }
        }

        public static void LaunchAppWindow()
        {
            try
            {
                // Check Microsoft Edge (App Mode: frameless, no tabs, standalone window)
                string edgePath = @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe";
                if (!File.Exists(edgePath))
                    edgePath = @"C:\Program Files\Microsoft\Edge\Application\msedge.exe";

                // Check Google Chrome (App Mode)
                string chromePath = @"C:\Program Files\Google\Chrome\Application\chrome.exe";
                if (!File.Exists(chromePath))
                    chromePath = @"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe";
                if (!File.Exists(chromePath))
                {
                    string localChrome = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), @"Google\Chrome\Application\chrome.exe");
                    if (File.Exists(localChrome)) chromePath = localChrome;
                }

                if (File.Exists(edgePath))
                {
                    Process.Start(new ProcessStartInfo(edgePath, string.Format("--app=\"{0}\" --window-size=1360,860", appUrl)) { UseShellExecute = true });
                    return;
                }
                else if (File.Exists(chromePath))
                {
                    Process.Start(new ProcessStartInfo(chromePath, string.Format("--app=\"{0}\" --window-size=1360,860", appUrl)) { UseShellExecute = true });
                    return;
                }
                else
                {
                    Process.Start(new ProcessStartInfo(appUrl) { UseShellExecute = true });
                }
            }
            catch
            {
                Process.Start(new ProcessStartInfo(appUrl) { UseShellExecute = true });
            }
        }

        static void StartBackgroundServer(string pythonExe, string scriptPath, string workingDir)
        {
            try
            {
                serverProcess = new Process();
                serverProcess.StartInfo.FileName = pythonExe;
                serverProcess.StartInfo.Arguments = "\"" + scriptPath + "\"";
                serverProcess.StartInfo.WorkingDirectory = workingDir;
                serverProcess.StartInfo.UseShellExecute = false;
                serverProcess.StartInfo.CreateNoWindow = true;
                serverProcess.StartInfo.RedirectStandardOutput = true;
                serverProcess.StartInfo.RedirectStandardError = true;

                string logPath = Path.Combine(workingDir, "server.log");
                FileStream fs = new FileStream(logPath, FileMode.Create, FileAccess.Write, FileShare.ReadWrite);
                logWriter = new StreamWriter(fs, System.Text.Encoding.UTF8) { AutoFlush = true };

                serverProcess.OutputDataReceived += (s, ev) =>
                {
                    if (ev.Data != null && logWriter != null)
                    {
                        lock (logLock)
                        {
                            try { logWriter.WriteLine(ev.Data); } catch { }
                        }
                    }
                };
                serverProcess.ErrorDataReceived += (s, ev) =>
                {
                    if (ev.Data != null && logWriter != null)
                    {
                        lock (logLock)
                        {
                            try { logWriter.WriteLine(ev.Data); } catch { }
                        }
                    }
                };

                serverProcess.Start();
                serverProcess.BeginOutputReadLine();
                serverProcess.BeginErrorReadLine();
            }
            catch (Exception ex)
            {
                try { File.WriteAllText(Path.Combine(workingDir, "server_error.log"), ex.ToString()); } catch { }
            }
        }

        static void StopBackgroundServer()
        {
            try
            {
                if (logWriter != null)
                {
                    try { logWriter.Flush(); logWriter.Close(); } catch { }
                    logWriter = null;
                }
                if (serverProcess != null && !serverProcess.HasExited)
                {
                    Process.Start(new ProcessStartInfo("taskkill", string.Format("/F /T /PID {0}", serverProcess.Id))
                    {
                        CreateNoWindow = true,
                        UseShellExecute = false
                    }).WaitForExit(2000);
                }
            }
            catch { }
        }

        static bool IsServerResponding()
        {
            try
            {
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create(appUrl + "/api/stats");
                req.Proxy = null; // CRITICAL: Bypasses 2000ms Windows WPAD proxy resolution
                req.Timeout = 1200;
                req.ReadWriteTimeout = 1200;
                using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                {
                    if (resp.StatusCode == HttpStatusCode.OK) return true;
                }
            }
            catch { }
            return false;
        }

        static bool IsPortListening(int port)
        {
            try
            {
                using (TcpClient client = new TcpClient())
                {
                    var res = client.BeginConnect("127.0.0.1", port, null, null);
                    bool ok = res.AsyncWaitHandle.WaitOne(200);
                    if (ok && client.Connected)
                    {
                        client.EndConnect(res);
                        return true;
                    }
                }
            }
            catch { }
            return false;
        }

        static void FreePort8000IfOccupied()
        {
            try
            {
                Process p = new Process();
                p.StartInfo.FileName = "powershell.exe";
                p.StartInfo.Arguments = "-NoProfile -Command \"Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | ForEach-Object { try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } catch {} }\"";
                p.StartInfo.CreateNoWindow = true;
                p.StartInfo.UseShellExecute = false;
                p.Start();
                p.WaitForExit(2000);
            }
            catch { }
        }

        static bool WaitForServerReady(SplashScreen splash, int timeoutSeconds)
        {
            int elapsedMs = 0;
            int totalMs = timeoutSeconds * 1000;

            while (elapsedMs < totalMs)
            {
                // If Python process died, abort wait immediately
                if (serverProcess != null && serverProcess.HasExited)
                {
                    return false;
                }

                // Fast check: is port listening and responding?
                if (IsPortListening(8000) && IsServerResponding())
                {
                    return true;
                }

                // Pump Windows messages continuously for 150ms in 25ms slices to prevent UI freeze
                DateTime slice = DateTime.Now;
                while ((DateTime.Now - slice).TotalMilliseconds < 150)
                {
                    Application.DoEvents();
                    Thread.Sleep(25);
                }
                elapsedMs += 150;

                if (splash != null)
                {
                    int sec = elapsedMs / 1000;
                    if (sec < 2)
                        splash.UpdateStatus("Starting Python computer vision engine...");
                    else if (sec < 5)
                        splash.UpdateStatus(string.Format("Loading YOLOv8 neural network & camera... ({0}s)", sec));
                    else
                        splash.UpdateStatus(string.Format("Initializing AI stream & web server... ({0}s)", sec));
                }
            }
            return false;
        }

        static void SetupSystemTray()
        {
            trayIcon = new NotifyIcon();
            trayIcon.Text = "AI Camera People Counter (Running)";

            string icoPath = Path.Combine(baseDir, "app.ico");
            if (File.Exists(icoPath))
            {
                try { trayIcon.Icon = new Icon(icoPath); } catch { trayIcon.Icon = SystemIcons.Application; }
            }
            else
            {
                trayIcon.Icon = SystemIcons.Application;
            }

            ContextMenuStrip menu = new ContextMenuStrip();
            menu.BackColor = Color.FromArgb(15, 23, 42);
            menu.ForeColor = Color.White;
            menu.ShowImageMargin = false;

            ToolStripMenuItem itemOpen = new ToolStripMenuItem("🖥️  Open Application Window");
            itemOpen.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            itemOpen.Click += (s, e) => LaunchAppWindow();
            menu.Items.Add(itemOpen);

            ToolStripMenuItem itemBrowser = new ToolStripMenuItem("🌐  Open in Web Browser");
            itemBrowser.Click += (s, e) => Process.Start(new ProcessStartInfo(appUrl) { UseShellExecute = true });
            menu.Items.Add(itemBrowser);

            menu.Items.Add(new ToolStripSeparator());

            ToolStripMenuItem itemReports = new ToolStripMenuItem("📁  Open Daily Reports Folder");
            itemReports.Click += (s, e) =>
            {
                string repDir = Path.Combine(baseDir, "daily_reports");
                if (!Directory.Exists(repDir)) Directory.CreateDirectory(repDir);
                Process.Start("explorer.exe", repDir);
            };
            menu.Items.Add(itemReports);

            ToolStripMenuItem itemRestart = new ToolStripMenuItem("🔄  Restart AI Service");
            itemRestart.Click += (s, e) =>
            {
                StopBackgroundServer();
                Thread.Sleep(1000);
                FreePort8000IfOccupied();
                string venvPython = Path.Combine(baseDir, ".venv", "Scripts", "python.exe");
                string appPy = Path.Combine(baseDir, "app.py");
                StartBackgroundServer(venvPython, appPy, baseDir);
                WaitForServerReady(null, 20);
                LaunchAppWindow();
            };
            menu.Items.Add(itemRestart);

            menu.Items.Add(new ToolStripSeparator());

            ToolStripMenuItem itemExit = new ToolStripMenuItem("❌  Exit Application");
            itemExit.ForeColor = Color.FromArgb(248, 113, 113);
            itemExit.Click += (s, e) =>
            {
                StopBackgroundServer();
                Application.Exit();
            };
            menu.Items.Add(itemExit);

            trayIcon.ContextMenuStrip = menu;
            trayIcon.Visible = true;

            trayIcon.DoubleClick += (s, e) => LaunchAppWindow();
            trayIcon.ShowBalloonTip(3000, "AI Camera People Counter", "Application is running continuously in the background. Access anytime from the system tray.", ToolTipIcon.Info);
        }

        static void EnsureDesktopShortcuts(string targetExe, string workDir)
        {
            try
            {
                string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
                string icoPath = Path.Combine(workDir, "app.ico");
                string iconArg = File.Exists(icoPath) ? icoPath : "shell32.dll,19";

                string[] candidateDesktops = new string[]
                {
                    Environment.GetFolderPath(Environment.SpecialFolder.Desktop),
                    Environment.GetFolderPath(Environment.SpecialFolder.CommonDesktopDirectory),
                    Path.Combine(userProfile, "Desktop"),
                    Path.Combine(userProfile, "OneDrive", "Desktop"),
                    Path.Combine(userProfile, "OneDrive", "Masaüstü")
                };

                bool needsCreation = false;
                foreach (string d in candidateDesktops)
                {
                    if (!string.IsNullOrEmpty(d) && Directory.Exists(d))
                    {
                        string sc = Path.Combine(d, "People Counter.lnk");
                        if (!File.Exists(sc))
                        {
                            needsCreation = true;
                            break;
                        }
                    }
                }

                if (!needsCreation) return;

                ThreadPool.QueueUserWorkItem((state) =>
                {
                    try
                    {
                        foreach (string d in candidateDesktops)
                        {
                            if (!string.IsNullOrEmpty(d) && Directory.Exists(d))
                            {
                                string sc = Path.Combine(d, "People Counter.lnk");
                                string psCmd = string.Format(
                                    "$w = New-Object -ComObject WScript.Shell; $s = $w.CreateShortcut('{0}'); $s.TargetPath = '{1}'; $s.WorkingDirectory = '{2}'; $s.Description = 'AI Camera People Counter & Revenue Tracker'; $s.IconLocation = '{3}'; $s.Save()",
                                    sc.Replace("'", "''"), targetExe.Replace("'", "''"), workDir.Replace("'", "''"), iconArg.Replace("'", "''")
                                );
                                Process p = new Process();
                                p.StartInfo.FileName = "powershell.exe";
                                p.StartInfo.Arguments = "-NoProfile -Command \"" + psCmd + "\"";
                                p.StartInfo.CreateNoWindow = true;
                                p.StartInfo.UseShellExecute = false;
                                p.Start();
                                p.WaitForExit(3000);
                            }
                        }
                    }
                    catch { }
                });
            }
            catch { }
        }
    }

    class SplashScreen : Form
    {
        private Label lblStatus;
        private ProgressBar progressBar;

        public SplashScreen()
        {
            this.Text = "AI Camera People Counter";
            this.FormBorderStyle = FormBorderStyle.None;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.Size = new Size(460, 210);
            this.BackColor = Color.FromArgb(15, 23, 42);
            this.TopMost = true;
            this.ShowInTaskbar = true;

            string icoPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "app.ico");
            if (File.Exists(icoPath))
            {
                try { this.Icon = new Icon(icoPath); } catch { }
            }

            this.Paint += (s, e) =>
            {
                using (Pen p = new Pen(Color.FromArgb(16, 185, 129), 2))
                {
                    e.Graphics.DrawRectangle(p, 1, 1, this.Width - 2, this.Height - 2);
                }
                using (Brush b = new SolidBrush(Color.FromArgb(16, 185, 129)))
                {
                    e.Graphics.FillRectangle(b, 0, 0, this.Width, 4);
                }
            };

            Label lblTitle = new Label();
            lblTitle.Text = "AI Camera People Counter";
            lblTitle.Font = new Font("Segoe UI", 16F, FontStyle.Bold);
            lblTitle.ForeColor = Color.White;
            lblTitle.Location = new Point(28, 30);
            lblTitle.Size = new Size(400, 35);
            this.Controls.Add(lblTitle);

            Label lblSub = new Label();
            lblSub.Text = "AI Vision & Real-Time Venue Revenue System";
            lblSub.Font = new Font("Segoe UI", 9F, FontStyle.Regular);
            lblSub.ForeColor = Color.FromArgb(56, 189, 248);
            lblSub.Location = new Point(30, 68);
            lblSub.Size = new Size(390, 20);
            this.Controls.Add(lblSub);

            lblStatus = new Label();
            lblStatus.Text = "Initializing AI vision engine and camera service...";
            lblStatus.Font = new Font("Segoe UI", 8.5F, FontStyle.Regular);
            lblStatus.ForeColor = Color.FromArgb(148, 163, 184);
            lblStatus.Location = new Point(30, 115);
            lblStatus.Size = new Size(400, 20);
            this.Controls.Add(lblStatus);

            progressBar = new ProgressBar();
            progressBar.Style = ProgressBarStyle.Marquee;
            progressBar.MarqueeAnimationSpeed = 25;
            progressBar.Location = new Point(30, 142);
            progressBar.Size = new Size(400, 14);
            this.Controls.Add(progressBar);
        }

        public void UpdateStatus(string message)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action<string>(UpdateStatus), message);
                return;
            }
            if (lblStatus != null && !lblStatus.IsDisposed)
            {
                lblStatus.Text = message;
            }
            Application.DoEvents();
        }
    }
}
