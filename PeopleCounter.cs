using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Threading;

namespace PeopleCounter
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.Title = "AI Camera People Counter & Revenue Tracker";
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string venvPython = Path.Combine(baseDir, ".venv", "Scripts", "python.exe");
            string appPy = Path.Combine(baseDir, "app.py");
            string setupBat = Path.Combine(baseDir, "Setup.bat");

            Console.WriteLine("=================================================================");
            Console.WriteLine("          AI CAMERA PEOPLE COUNTER & REVENUE TRACKER");
            Console.WriteLine("=================================================================");
            Console.WriteLine();

            string localAppDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "PeopleCounter");
            string localAppPy = Path.Combine(localAppDir, "app.py");
            string localAppExe = Path.Combine(localAppDir, "PeopleCounter.exe");
            string localVenvPython = Path.Combine(localAppDir, ".venv", "Scripts", "python.exe");

            // If app.py does not exist in the current folder (e.g. executed from Temp or standalone):
            if (!File.Exists(appPy))
            {
                // Check if already installed in LocalAppData
                if (File.Exists(localAppPy) && File.Exists(localAppExe))
                {
                    Console.WriteLine("[INFO] People Counter is installed at: " + localAppDir);
                    Console.WriteLine("[INFO] Redirecting execution to installed application...");
                    try
                    {
                        Process p = new Process();
                        p.StartInfo.FileName = localAppExe;
                        p.StartInfo.WorkingDirectory = localAppDir;
                        p.StartInfo.UseShellExecute = true;
                        p.Start();
                        return;
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine("[WARN] Could not launch installed exe: " + ex.Message);
                    }
                }

                // Check if PeopleCounter-Setup.exe exists locally
                string localSetup = Path.Combine(baseDir, "PeopleCounter-Setup.exe");
                if (!File.Exists(localSetup))
                {
                    DirectoryInfo parentInfo = Directory.GetParent(baseDir);
                    string parentDir = parentInfo != null ? parentInfo.FullName : "";
                    string parentSetup = Path.Combine(parentDir, "PeopleCounter-Setup.exe");
                    if (File.Exists(parentSetup)) localSetup = parentSetup;
                }

                if (File.Exists(localSetup))
                {
                    Console.WriteLine("[INFO] Running installer: " + localSetup);
                    Process.Start(new ProcessStartInfo(localSetup, "/auto") { UseShellExecute = true });
                    return;
                }

                // Download PeopleCounter-Setup.exe directly
                Console.WriteLine("[INFO] Application files not found. Downloading clean installer...");
                Console.WriteLine("[INFO] Please wait a moment while setup is prepared...");
                string setupUrl = "https://github.com/HasanKaan28/kamera-kisi-sayaci/releases/latest/download/PeopleCounter-Setup.exe";
                string tempSetup = Path.Combine(Path.GetTempPath(), "PeopleCounter-Setup.exe");

                try
                {
                    ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072;
                    using (WebClient client = new WebClient())
                    {
                        client.Headers.Add("User-Agent", "PeopleCounter-Bootstrap");
                        client.DownloadFile(setupUrl, tempSetup);
                    }
                    Console.WriteLine("[OK] Installer downloaded. Starting setup wizard...");
                    Process.Start(new ProcessStartInfo(tempSetup, "/auto") { UseShellExecute = true });
                    return;
                }
                catch (Exception ex)
                {
                    Console.ForegroundColor = ConsoleColor.Yellow;
                    Console.WriteLine("[ERROR] Could not auto-download installer: " + ex.Message);
                    Console.WriteLine("Please download 'PeopleCounter-Setup.exe' directly from:");
                    Console.WriteLine("https://github.com/HasanKaan28/kamera-kisi-sayaci/releases/latest");
                    Console.ResetColor();
                    Console.WriteLine();
                    Console.WriteLine("Press any key to exit...");
                    Console.ReadKey();
                    return;
                }
            }

            // If app.py exists here, verify virtual environment (.venv)
            if (!File.Exists(venvPython))
            {
                // If this is running in another folder but localApp has .venv, we can use localVenvPython
                if (File.Exists(localVenvPython))
                {
                    venvPython = localVenvPython;
                }
                else
                {
                    Console.WriteLine("[NOTICE] Virtual environment (.venv) not found. Running automated setup...");
                    string setupExe = Path.Combine(baseDir, "PeopleCounter-Setup.exe");
                    if (File.Exists(setupExe))
                    {
                        Process p = Process.Start(new ProcessStartInfo(setupExe, "/auto") { UseShellExecute = true });
                        p.WaitForExit();
                    }
                    else if (File.Exists(setupBat))
                    {
                        Process setupProc = new Process();
                        setupProc.StartInfo.FileName = "cmd.exe";
                        setupProc.StartInfo.Arguments = "/c \"" + setupBat + "\"";
                        setupProc.StartInfo.WorkingDirectory = baseDir;
                        setupProc.StartInfo.UseShellExecute = false;
                        setupProc.Start();
                        setupProc.WaitForExit();
                    }
                    else
                    {
                        // Direct python setup fallback
                        Console.WriteLine("[INFO] Creating virtual environment (.venv)...");
                        Process p = new Process();
                        p.StartInfo.FileName = "powershell.exe";
                        p.StartInfo.Arguments = "-NoProfile -Command \"python -m venv .venv; .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt\"";
                        p.StartInfo.WorkingDirectory = baseDir;
                        p.StartInfo.UseShellExecute = false;
                        p.Start();
                        p.WaitForExit();
                    }

                    if (!File.Exists(venvPython))
                    {
                        Console.WriteLine("[ERROR] Setup could not be completed automatically.");
                        Console.WriteLine("Please run 'PeopleCounter-Setup.exe' to perform a clean setup.");
                        Console.WriteLine("Press any key to exit...");
                        Console.ReadKey();
                        return;
                    }
                }
            }

            Console.WriteLine("Starting AI People Counter server...");
            Console.WriteLine("Web Dashboard: http://localhost:8000");
            Console.WriteLine();

            // Open browser in background thread
            new Thread(() =>
            {
                Thread.Sleep(2500);
                try
                {
                    Process.Start(new ProcessStartInfo("http://localhost:8000") { UseShellExecute = true });
                }
                catch { }
            }).Start();

            // Run app.py using virtual environment Python
            try
            {
                Process appProc = new Process();
                appProc.StartInfo.FileName = venvPython;
                appProc.StartInfo.Arguments = "\"" + appPy + "\"";
                appProc.StartInfo.WorkingDirectory = baseDir;
                appProc.StartInfo.UseShellExecute = false;
                appProc.Start();
                appProc.WaitForExit();
            }
            catch (Exception ex)
            {
                Console.WriteLine("[ERROR] Failed to start application: " + ex.Message);
                Console.WriteLine("Press any key to exit...");
                Console.ReadKey();
            }
        }
    }
}
