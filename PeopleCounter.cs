using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;

namespace PeopleCounter
{
    static class Program
    {
        private static Mutex appMutex = null;
        private static Process serverProcess = null;
        private static NotifyIcon trayIcon = null;
        private static string appUrl = "http://localhost:8000";
        private static string baseDir = "";

        [STAThread]
        static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            baseDir = AppDomain.CurrentDomain.BaseDirectory;

            // 1. Single-Instance Mutex: prevents duplicate instances & port conflicts
            bool createdNew;
            appMutex = new Mutex(true, "Global\\PeopleCounter_AI_Vision_App_Mutex_v1", out createdNew);
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

                MessageBox.Show("AI Kamera Kişi Sayacı kurulum dosyaları bulunamadı.\nLütfen 'PeopleCounter-Setup.exe' dosyasını çalıştırın.",
                                "Kurulum Gerekli", MessageBoxButtons.OK, MessageBoxIcon.Information);
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
                        MessageBox.Show("Python sanal ortamı (.venv) bulunamadı. Lütfen PeopleCounter-Setup.exe ile kurulum yapın.",
                                        "Kurulum Eksik", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        return;
                    }
                }
            }

            // Ensure verified Desktop Shortcuts with custom icon
            EnsureDesktopShortcuts(Path.Combine(baseDir, "PeopleCounter.exe"), baseDir);

            // 2. Show Sleek Native Splash Screen while Python & YOLO are loading
            using (SplashScreen splash = new SplashScreen())
            {
                splash.Show();
                Application.DoEvents();

                // Start Python in background silently (NO black CMD console window!)
                StartBackgroundServer(venvPython, appPy, baseDir);

                // Wait until server is responding at http://localhost:8000 (poll /api/stats)
                bool isReady = WaitForServerReady(35);

                splash.Close();

                if (!isReady)
                {
                    MessageBox.Show("Yapay zeka kamera servisi başlatılamadı. Lütfen 'server.log' dosyasını kontrol edin.",
                                    "Başlatma Hatası", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    StopBackgroundServer();
                    return;
                }
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
                StreamWriter sw = new StreamWriter(logPath, false);
                sw.AutoFlush = true;

                serverProcess.OutputDataReceived += (s, ev) => { if (ev.Data != null) sw.WriteLine(ev.Data); };
                serverProcess.ErrorDataReceived += (s, ev) => { if (ev.Data != null) sw.WriteLine(ev.Data); };

                serverProcess.Start();
                serverProcess.BeginOutputReadLine();
                serverProcess.BeginErrorReadLine();
            }
            catch (Exception ex)
            {
                File.WriteAllText(Path.Combine(workingDir, "server_error.log"), ex.ToString());
            }
        }

        static void StopBackgroundServer()
        {
            try
            {
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

        static bool WaitForServerReady(int timeoutSeconds)
        {
            int elapsed = 0;
            while (elapsed < timeoutSeconds * 2)
            {
                try
                {
                    HttpWebRequest req = (HttpWebRequest)WebRequest.Create(appUrl + "/api/stats");
                    req.Timeout = 800;
                    using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                    {
                        if (resp.StatusCode == HttpStatusCode.OK) return true;
                    }
                }
                catch { }
                Thread.Sleep(500);
                elapsed++;
            }
            return false;
        }

        static void SetupSystemTray()
        {
            trayIcon = new NotifyIcon();
            trayIcon.Text = "AI Kamera Kişi Sayacı (Çalışıyor)";

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

            ToolStripMenuItem itemOpen = new ToolStripMenuItem("🖥️  Programı Aç (Pencere)");
            itemOpen.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            itemOpen.Click += (s, e) => LaunchAppWindow();
            menu.Items.Add(itemOpen);

            ToolStripMenuItem itemBrowser = new ToolStripMenuItem("🌐  Tarayıcıda Aç");
            itemBrowser.Click += (s, e) => Process.Start(new ProcessStartInfo(appUrl) { UseShellExecute = true });
            menu.Items.Add(itemBrowser);

            menu.Items.Add(new ToolStripSeparator());

            ToolStripMenuItem itemReports = new ToolStripMenuItem("📁  Raporlar Klasörünü Aç");
            itemReports.Click += (s, e) =>
            {
                string repDir = Path.Combine(baseDir, "daily_reports");
                if (!Directory.Exists(repDir)) Directory.CreateDirectory(repDir);
                Process.Start("explorer.exe", repDir);
            };
            menu.Items.Add(itemReports);

            ToolStripMenuItem itemRestart = new ToolStripMenuItem("🔄  Servisi Yeniden Başlat");
            itemRestart.Click += (s, e) =>
            {
                StopBackgroundServer();
                Thread.Sleep(1000);
                string venvPython = Path.Combine(baseDir, ".venv", "Scripts", "python.exe");
                string appPy = Path.Combine(baseDir, "app.py");
                StartBackgroundServer(venvPython, appPy, baseDir);
                WaitForServerReady(20);
                LaunchAppWindow();
            };
            menu.Items.Add(itemRestart);

            menu.Items.Add(new ToolStripSeparator());

            ToolStripMenuItem itemExit = new ToolStripMenuItem("❌  Programdan Tamamen Çık");
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
            trayIcon.ShowBalloonTip(3000, "AI Kamera Kişi Sayacı", "Program arka planda kesintisiz çalışıyor. Simgeden kontrol edebilirsiniz.", ToolTipIcon.Info);
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
        }
    }

    class SplashScreen : Form
    {
        public SplashScreen()
        {
            this.Text = "AI Kamera Kişi Sayacı";
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
            lblTitle.Text = "AI Kamera Kişi Sayacı";
            lblTitle.Font = new Font("Segoe UI", 16F, FontStyle.Bold);
            lblTitle.ForeColor = Color.White;
            lblTitle.Location = new Point(28, 30);
            lblTitle.Size = new Size(400, 35);
            this.Controls.Add(lblTitle);

            Label lblSub = new Label();
            lblSub.Text = "Yapay Zeka Görüşü & Canlı Kasa Takip Sistemi";
            lblSub.Font = new Font("Segoe UI", 9F, FontStyle.Regular);
            lblSub.ForeColor = Color.FromArgb(56, 189, 248);
            lblSub.Location = new Point(30, 68);
            lblSub.Size = new Size(390, 20);
            this.Controls.Add(lblSub);

            Label lblStatus = new Label();
            lblStatus.Text = "Sistem ve yapay zeka servisi başlatılıyor...";
            lblStatus.Font = new Font("Segoe UI", 8.5F, FontStyle.Regular);
            lblStatus.ForeColor = Color.FromArgb(148, 163, 184);
            lblStatus.Location = new Point(30, 115);
            lblStatus.Size = new Size(390, 18);
            this.Controls.Add(lblStatus);

            ProgressBar pb = new ProgressBar();
            pb.Style = ProgressBarStyle.Marquee;
            pb.MarqueeAnimationSpeed = 25;
            pb.Location = new Point(30, 142);
            pb.Size = new Size(400, 14);
            this.Controls.Add(pb);
        }
    }
}
