using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;

namespace PeopleCounterInstaller
{
    public class SetupForm : Form
    {
        private TextBox txtDir;
        private Button btnBrowse;
        private Button btnInstall;
        private Button btnClose;
        private ProgressBar progressBar;
        private Label lblStatus;
        private TextBox txtLog;
        private CheckBox chkLaunch;
        private BackgroundWorker worker;
        private bool autoStart = false;

        [STAThread]
        public static void Main(string[] args)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            bool auto = (args.Length > 0 && (args[0] == "/auto" || args[0] == "/silent" || args[0] == "-y"));
            Application.Run(new SetupForm(auto));
        }

        public SetupForm(bool auto = false)
        {
            this.autoStart = auto;
            InitializeComponent();
            this.Shown += (s, e) =>
            {
                if (this.autoStart)
                {
                    BtnInstall_Click(this, EventArgs.Empty);
                }
            };
        }

        private void InitializeComponent()
        {
            bool isTr = System.Globalization.CultureInfo.CurrentUICulture.TwoLetterISOLanguageName.Equals("tr", StringComparison.OrdinalIgnoreCase);
            this.Text = isTr ? "AI Kişi Sayacı & Ciro Takip - Kurulum Sihirbazı" : "AI Camera People Counter - Setup Wizard";
            this.Size = new Size(580, 520);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.BackColor = Color.FromArgb(15, 23, 42); // Slate-950
            this.ForeColor = Color.White;
            this.Font = new Font("Segoe UI", 9F, FontStyle.Regular);

            // Header Panel
            Panel pnlHeader = new Panel();
            pnlHeader.Dock = DockStyle.Top;
            pnlHeader.Height = 70;
            pnlHeader.BackColor = Color.FromArgb(30, 41, 59); // Slate-800
            this.Controls.Add(pnlHeader);

            Label lblTitle = new Label();
            lblTitle.Text = isTr ? "AI Kamera Kişi Sayacı & Gelir Takip Sistemi" : "AI Camera People Counter & Revenue Tracker";
            lblTitle.Font = new Font("Segoe UI", 12F, FontStyle.Bold);
            lblTitle.ForeColor = Color.FromArgb(16, 185, 129); // Emerald-500
            lblTitle.Location = new Point(20, 12);
            lblTitle.AutoSize = true;
            pnlHeader.Controls.Add(lblTitle);

            Label lblSubtitle = new Label();
            lblSubtitle.Text = isTr ? "Tek Tıkla Otomatik Kurulum Sihirbazı & Çalıştırıcı" : "One-Click Automated Setup Wizard & Dependency Installer";
            lblSubtitle.Font = new Font("Segoe UI", 8.5F, FontStyle.Regular);
            lblSubtitle.ForeColor = Color.FromArgb(148, 163, 184); // Slate-400
            lblSubtitle.Location = new Point(22, 38);
            lblSubtitle.AutoSize = true;
            pnlHeader.Controls.Add(lblSubtitle);

            // Main Container
            int top = 85;

            // Destination Folder Label
            Label lblDest = new Label();
            lblDest.Text = isTr ? "Kurulum Dizini (Varsayılan):" : "Installation Directory:";
            lblDest.Location = new Point(20, top);
            lblDest.AutoSize = true;
            lblDest.ForeColor = Color.FromArgb(226, 232, 240);
            this.Controls.Add(lblDest);

            top += 22;

            // Destination TextBox
            txtDir = new TextBox();
            string defaultDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "PeopleCounter");
            txtDir.Text = defaultDir;
            txtDir.Location = new Point(20, top);
            txtDir.Size = new Size(420, 25);
            txtDir.BackColor = Color.FromArgb(2, 6, 23);
            txtDir.ForeColor = Color.FromArgb(248, 250, 252);
            txtDir.BorderStyle = BorderStyle.FixedSingle;
            this.Controls.Add(txtDir);

            // Browse Button
            btnBrowse = new Button();
            btnBrowse.Text = isTr ? "Gözat..." : "Browse...";
            btnBrowse.Location = new Point(450, top - 1);
            btnBrowse.Size = new Size(95, 27);
            btnBrowse.BackColor = Color.FromArgb(51, 65, 85);
            btnBrowse.ForeColor = Color.White;
            btnBrowse.FlatStyle = FlatStyle.Flat;
            btnBrowse.FlatAppearance.BorderSize = 0;
            btnBrowse.Click += BtnBrowse_Click;
            this.Controls.Add(btnBrowse);

            top += 38;

            // Progress Status Label
            lblStatus = new Label();
            lblStatus.Text = isTr ? "Kuruluma hazır. 'Kurulumu Başlat' butonuna tıklayın." : "Ready to install. Click 'Install & Launch' to start.";
            lblStatus.Location = new Point(20, top);
            lblStatus.Size = new Size(525, 20);
            lblStatus.ForeColor = Color.FromArgb(56, 189, 248); // Sky-400
            lblStatus.Font = new Font("Segoe UI", 8.5F, FontStyle.Bold);
            this.Controls.Add(lblStatus);

            top += 22;

            // Progress Bar
            progressBar = new ProgressBar();
            progressBar.Location = new Point(20, top);
            progressBar.Size = new Size(525, 18);
            progressBar.Value = 0;
            this.Controls.Add(progressBar);

            top += 28;

            // Output Log TextBox
            txtLog = new TextBox();
            txtLog.Location = new Point(20, top);
            txtLog.Size = new Size(525, 175);
            txtLog.Multiline = true;
            txtLog.ScrollBars = ScrollBars.Vertical;
            txtLog.ReadOnly = true;
            txtLog.BackColor = Color.FromArgb(2, 6, 23);
            txtLog.ForeColor = Color.FromArgb(148, 163, 184);
            txtLog.Font = new Font("Consolas", 8F);
            txtLog.BorderStyle = BorderStyle.FixedSingle;
            this.Controls.Add(txtLog);

            top += 185;

            // Checkbox: Launch after finish
            chkLaunch = new CheckBox();
            chkLaunch.Text = isTr ? "Kurulum bittiğinde program otomatik açılsın" : "Launch People Counter immediately when finished";
            chkLaunch.Checked = true;
            chkLaunch.Location = new Point(20, top);
            chkLaunch.AutoSize = true;
            chkLaunch.ForeColor = Color.FromArgb(226, 232, 240);
            this.Controls.Add(chkLaunch);

            // Install & Launch Button
            btnInstall = new Button();
            btnInstall.Text = isTr ? "Kurulumu Başlat" : "Install & Launch";
            btnInstall.Location = new Point(320, top - 3);
            btnInstall.Size = new Size(135, 34);
            btnInstall.BackColor = Color.FromArgb(16, 185, 129); // Emerald-500
            btnInstall.ForeColor = Color.White;
            btnInstall.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold);
            btnInstall.FlatStyle = FlatStyle.Flat;
            btnInstall.FlatAppearance.BorderSize = 0;
            btnInstall.Click += BtnInstall_Click;
            this.Controls.Add(btnInstall);

            // Close Button
            btnClose = new Button();
            btnClose.Text = isTr ? "İptal" : "Cancel";
            btnClose.Location = new Point(465, top - 3);
            btnClose.Size = new Size(80, 34);
            btnClose.BackColor = Color.FromArgb(51, 65, 85);
            btnClose.ForeColor = Color.White;
            btnClose.FlatStyle = FlatStyle.Flat;
            btnClose.FlatAppearance.BorderSize = 0;
            btnClose.Click += (s, e) => this.Close();
            this.Controls.Add(btnClose);

            // Worker Thread
            worker = new BackgroundWorker();
            worker.WorkerReportsProgress = true;
            worker.DoWork += Worker_DoWork;
            worker.ProgressChanged += Worker_ProgressChanged;
            worker.RunWorkerCompleted += Worker_RunWorkerCompleted;
        }

        private void BtnBrowse_Click(object sender, EventArgs e)
        {
            using (FolderBrowserDialog dlg = new FolderBrowserDialog())
            {
                dlg.Description = "Select installation folder for People Counter:";
                dlg.SelectedPath = txtDir.Text;
                if (dlg.ShowDialog() == DialogResult.OK)
                {
                    txtDir.Text = dlg.SelectedPath;
                }
            }
        }

        private void BtnInstall_Click(object sender, EventArgs e)
        {
            btnInstall.Enabled = false;
            btnBrowse.Enabled = false;
            txtDir.ReadOnly = true;
            btnClose.Text = "Close";
            btnClose.Enabled = false;

            txtLog.Clear();
            worker.RunWorkerAsync(txtDir.Text.Trim());
        }

        private void AppendLog(string message)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action<string>(AppendLog), message);
                return;
            }
            txtLog.AppendText(message + Environment.NewLine);
            txtLog.SelectionStart = txtLog.Text.Length;
            txtLog.ScrollToCaret();
        }

        private void Worker_ProgressChanged(object sender, ProgressChangedEventArgs e)
        {
            progressBar.Value = Math.Min(Math.Max(e.ProgressPercentage, 0), 100);
            if (e.UserState != null)
            {
                lblStatus.Text = e.UserState.ToString();
            }
        }

        private void Worker_DoWork(object sender, DoWorkEventArgs e)
        {
            string targetDir = (string)e.Argument;

            try
            {
                // -------------------------------------------------------------
                // STEP 1: Extract Embedded Package
                // -------------------------------------------------------------
                worker.ReportProgress(10, "Extracting application package...");
                AppendLog("[1/5] Creating installation directory: " + targetDir);
                Directory.CreateDirectory(targetDir);

                var assembly = Assembly.GetExecutingAssembly();
                using (Stream stream = assembly.GetManifestResourceStream("payload.zip"))
                {
                    if (stream == null)
                    {
                        throw new Exception("Embedded package payload.zip not found in installer binary.");
                    }

                    using (ZipArchive archive = new ZipArchive(stream))
                    {
                        foreach (ZipArchiveEntry entry in archive.Entries)
                        {
                            string destinationPath = Path.Combine(targetDir, entry.FullName);
                            string dir = Path.GetDirectoryName(destinationPath);
                            if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);

                            if (!string.IsNullOrEmpty(entry.Name))
                            {
                                entry.ExtractToFile(destinationPath, true);
                            }
                        }
                    }
                }
                AppendLog("[OK] All project files extracted successfully.");

                // -------------------------------------------------------------
                // STEP 2: Detect or Auto-Install Python
                // -------------------------------------------------------------
                worker.ReportProgress(25, "Verifying Python environment...");
                AppendLog("[2/5] Checking Python installation...");

                string pythonExe = FindPythonExecutable();
                if (string.IsNullOrEmpty(pythonExe))
                {
                    worker.ReportProgress(30, "Python not found. Downloading Python 3.11...");
                    AppendLog("Python 3.10+ was not found on your system.");
                    AppendLog("Downloading official Python 3.11 installer from python.org...");

                    string pyInstallerPath = Path.Combine(Path.GetTempPath(), "python-3.11.9-amd64.exe");
                    string pyUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe";

                    ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072; // TLS 1.2
                    using (WebClient client = new WebClient())
                    {
                        client.Headers.Add("User-Agent", "PeopleCounter-Installer");
                        client.DownloadFile(pyUrl, pyInstallerPath);
                    }
                    AppendLog("[OK] Python installer downloaded.");

                    worker.ReportProgress(40, "Installing Python 3.11, please wait...");
                    AppendLog("Running silent Python installation...");

                    Process pyProc = new Process();
                    pyProc.StartInfo.FileName = pyInstallerPath;
                    pyProc.StartInfo.Arguments = "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0 SimpleInstall=1";
                    pyProc.StartInfo.UseShellExecute = false;
                    pyProc.Start();
                    pyProc.WaitForExit();

                    if (File.Exists(pyInstallerPath)) File.Delete(pyInstallerPath);

                    // Re-check
                    pythonExe = FindPythonExecutable();
                    if (string.IsNullOrEmpty(pythonExe))
                    {
                        string localPy = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python", "Python311", "python.exe");
                        if (File.Exists(localPy)) pythonExe = localPy;
                    }

                    if (string.IsNullOrEmpty(pythonExe))
                    {
                        throw new Exception("Python could not be verified after installation. Please install Python 3.11 manually.");
                    }
                    AppendLog("[OK] Python 3.11 installed successfully: " + pythonExe);
                }
                else
                {
                    AppendLog("[OK] Python detected: " + pythonExe);
                }

                // -------------------------------------------------------------
                // STEP 3: Create Virtual Environment (.venv)
                // -------------------------------------------------------------
                worker.ReportProgress(50, "Setting up virtual environment (.venv)...");
                AppendLog("[3/5] Setting up virtual environment in: " + targetDir);

                string venvDir = Path.Combine(targetDir, ".venv");
                string venvPython = Path.Combine(venvDir, "Scripts", "python.exe");

                if (!File.Exists(venvPython))
                {
                    AppendLog("Creating Python virtual environment (.venv)...");
                    ExecuteProcess(pythonExe, "-m venv \"" + venvDir + "\"", targetDir);

                    if (!File.Exists(venvPython))
                    {
                        throw new Exception("Failed to initialize virtual environment (.venv).");
                    }
                    AppendLog("[OK] Virtual environment (.venv) created successfully.");
                }
                else
                {
                    AppendLog("[OK] Virtual environment already exists.");
                }

                // -------------------------------------------------------------
                // STEP 4: Install AI Vision Dependencies
                // -------------------------------------------------------------
                worker.ReportProgress(65, "Installing AI Vision dependencies (this may take a few minutes)...");
                AppendLog("[4/5] Installing dependencies from requirements.txt...");
                AppendLog("(Downloading PyTorch, YOLOv8, OpenCV, FastAPI, etc. Please wait...)");

                ExecuteProcess(venvPython, "-m pip install --upgrade pip --quiet", targetDir);
                ExecuteProcess(venvPython, "-m pip install -r requirements.txt", targetDir);

                AppendLog("[OK] All dependencies installed successfully.");

                // -------------------------------------------------------------
                // STEP 5: Create Desktop & Start Menu Shortcuts
                // -------------------------------------------------------------
                worker.ReportProgress(88, "Creating Desktop shortcuts...");
                AppendLog("[5/5] Creating application shortcuts...");

                string installedExe = Path.Combine(targetDir, "PeopleCounter.exe");
                string desktop = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
                string shortcutPath = Path.Combine(desktop, "People Counter.lnk");

                CreateShortcut(shortcutPath, installedExe, targetDir, "AI Camera People Counter & Revenue Tracker");
                AppendLog("[OK] Desktop shortcut created: 'People Counter'");

                string startMenu = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.StartMenu), "Programs");
                string smShortcut = Path.Combine(startMenu, "People Counter.lnk");
                CreateShortcut(smShortcut, installedExe, targetDir, "AI Camera People Counter & Revenue Tracker");
                AppendLog("[OK] Start Menu shortcut created.");

                worker.ReportProgress(100, "Setup Completed Successfully!");
                AppendLog(Environment.NewLine + "=================================================");
                AppendLog("  INSTALLATION COMPLETED SUCCESSFULLY!");
                AppendLog("=================================================");

                e.Result = targetDir;
            }
            catch (Exception ex)
            {
                AppendLog(Environment.NewLine + "[ERROR] " + ex.Message);
                throw;
            }
        }

        private void Worker_RunWorkerCompleted(object sender, RunWorkerCompletedEventArgs e)
        {
            btnClose.Enabled = true;
            btnClose.Text = "Exit";

            if (e.Error != null)
            {
                lblStatus.Text = "Installation failed: " + e.Error.Message;
                lblStatus.ForeColor = Color.FromArgb(248, 113, 113); // Red-400
                btnInstall.Enabled = true;
                btnBrowse.Enabled = true;
                txtDir.ReadOnly = false;
                MessageBox.Show("An error occurred during installation:\n\n" + e.Error.Message, "Installation Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            else
            {
                lblStatus.Text = "Installation Complete! (100%)";
                lblStatus.ForeColor = Color.FromArgb(52, 211, 153); // Emerald-400
                string targetDir = (string)e.Result;
                string installedExe = Path.Combine(targetDir, "PeopleCounter.exe");

                if (chkLaunch.Checked && File.Exists(installedExe))
                {
                    try
                    {
                        Process.Start(new ProcessStartInfo(installedExe) { WorkingDirectory = targetDir });
                    }
                    catch { }
                }

                MessageBox.Show(
                    "AI Camera People Counter has been installed successfully!\n\nYou can launch it anytime from the 'People Counter' shortcut on your Desktop.",
                    "Setup Complete",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
            }
        }

        private string FindPythonExecutable()
        {
            // 1. Try PATH
            try
            {
                Process p = new Process();
                p.StartInfo.FileName = "python.exe";
                p.StartInfo.Arguments = "--version";
                p.StartInfo.UseShellExecute = false;
                p.StartInfo.RedirectStandardOutput = true;
                p.StartInfo.RedirectStandardError = true;
                p.StartInfo.CreateNoWindow = true;
                p.Start();
                p.WaitForExit(2000);
                if (p.ExitCode == 0) return "python.exe";
            }
            catch { }

            try
            {
                Process p = new Process();
                p.StartInfo.FileName = "py.exe";
                p.StartInfo.Arguments = "-3 --version";
                p.StartInfo.UseShellExecute = false;
                p.StartInfo.RedirectStandardOutput = true;
                p.StartInfo.RedirectStandardError = true;
                p.StartInfo.CreateNoWindow = true;
                p.Start();
                p.WaitForExit(2000);
                if (p.ExitCode == 0) return "py.exe";
            }
            catch { }

            // 2. Known Windows standard locations
            string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            string[] candidatePaths = new string[]
            {
                Path.Combine(localApp, "Programs", "Python", "Python312", "python.exe"),
                Path.Combine(localApp, "Programs", "Python", "Python311", "python.exe"),
                Path.Combine(localApp, "Programs", "Python", "Python310", "python.exe"),
                @"C:\Python312\python.exe",
                @"C:\Python311\python.exe",
                @"C:\Python310\python.exe",
                @"C:\Program Files\Python312\python.exe",
                @"C:\Program Files\Python311\python.exe",
                @"C:\Program Files\Python310\python.exe"
            };

            foreach (string path in candidatePaths)
            {
                if (File.Exists(path)) return path;
            }

            return null;
        }

        private void ExecuteProcess(string fileName, string arguments, string workingDir)
        {
            Process proc = new Process();
            proc.StartInfo.FileName = fileName;
            proc.StartInfo.Arguments = arguments;
            proc.StartInfo.WorkingDirectory = workingDir;
            proc.StartInfo.UseShellExecute = false;
            proc.StartInfo.RedirectStandardOutput = true;
            proc.StartInfo.RedirectStandardError = true;
            proc.StartInfo.CreateNoWindow = true;

            proc.OutputDataReceived += (s, ev) => { if (!string.IsNullOrEmpty(ev.Data)) AppendLog(ev.Data); };
            proc.ErrorDataReceived += (s, ev) => { if (!string.IsNullOrEmpty(ev.Data)) AppendLog(ev.Data); };

            proc.Start();
            proc.BeginOutputReadLine();
            proc.BeginErrorReadLine();
            proc.WaitForExit();

            if (proc.ExitCode != 0)
            {
                throw new Exception(string.Format("Process {0} {1} exited with error code {2}.", fileName, arguments, proc.ExitCode));
            }
        }

        private void CreateShortcut(string shortcutPath, string targetPath, string workingDir, string description)
        {
            try
            {
                string psCmd = string.Format(
                    "$w = New-Object -ComObject WScript.Shell; $s = $w.CreateShortcut('{0}'); $s.TargetPath = '{1}'; $s.WorkingDirectory = '{2}'; $s.Description = '{3}'; $s.IconLocation = 'shell32.dll,19'; $s.Save()",
                    shortcutPath.Replace("'", "''"),
                    targetPath.Replace("'", "''"),
                    workingDir.Replace("'", "''"),
                    description.Replace("'", "''")
                );
                Process proc = new Process();
                proc.StartInfo.FileName = "powershell.exe";
                proc.StartInfo.Arguments = "-NoProfile -ExecutionPolicy Bypass -Command \"" + psCmd + "\"";
                proc.StartInfo.CreateNoWindow = true;
                proc.StartInfo.UseShellExecute = false;
                proc.Start();
                proc.WaitForExit(5000);
            }
            catch { }
        }
    }
}
