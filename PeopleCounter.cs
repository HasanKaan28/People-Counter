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

            // 1. Check if running inside Windows temporary ZIP preview folder
            bool isTempOrZip = baseDir.IndexOf("Temp", StringComparison.OrdinalIgnoreCase) >= 0 ||
                               baseDir.IndexOf(".zip", StringComparison.OrdinalIgnoreCase) >= 0;

            if (isTempOrZip && (!File.Exists(setupBat) || !File.Exists(appPy)))
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("=================================================================");
                Console.WriteLine("           [HATA] ZIP DOSYASI AYIKLANMAMIŞ!");
                Console.WriteLine("         [ERROR] ZIP ARCHIVE NOT EXTRACTED!");
                Console.WriteLine("=================================================================");
                Console.ResetColor();
                Console.WriteLine();
                Console.ForegroundColor = ConsoleColor.Yellow;
                Console.WriteLine("PeopleCounter.exe dosyasını ZIP dosyasının içinden doğrudan");
                Console.WriteLine("çalıştırdınız. Windows diğer dosyaları geçici klasöre taşımadı.");
                Console.WriteLine();
                Console.WriteLine("ÇÖZÜM ADIMLARI:");
                Console.WriteLine("1. İndirdiğiniz 'PeopleCounter-v1.1.0-Windows.zip' dosyasına SAĞ TIKLAYIN.");
                Console.WriteLine("2. 'Tümünü Ayıkla...' (Extract All) seçeneğine tıklayın.");
                Console.WriteLine("3. Çıkarılan klasörün içine girip 'PeopleCounter.exe'yi oradan çalıştırın.");
                Console.WriteLine();
                Console.WriteLine("-----------------------------------------------------------------");
                Console.WriteLine("HOW TO FIX:");
                Console.WriteLine("1. Right-click the downloaded 'PeopleCounter-v1.1.0-Windows.zip'.");
                Console.WriteLine("2. Click 'Extract All...'.");
                Console.WriteLine("3. Open the extracted folder and run 'PeopleCounter.exe' from there.");
                Console.ResetColor();
                Console.WriteLine();
                Console.WriteLine("Press any key to exit / Çıkmak için bir tuşa basın...");
                Console.ReadKey();
                return;
            }

            // 2. If app files are missing (e.g. user downloaded only PeopleCounter.exe), auto-download package
            if (!File.Exists(setupBat) || !File.Exists(appPy))
            {
                Console.WriteLine("[INFO] Application files not found in: " + baseDir);
                Console.WriteLine("[INFO] Downloading full package from GitHub release, please wait...");
                Console.WriteLine();

                string zipUrl = "https://github.com/HasanKaan28/kamera-kisi-sayaci/releases/download/v1.1.0/PeopleCounter-v1.1.0-Windows.zip";
                string tempZip = Path.Combine(baseDir, "package_download.zip");

                try
                {
                    ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072; // TLS 1.2
                    using (WebClient client = new WebClient())
                    {
                        client.Headers.Add("User-Agent", "PeopleCounter-Launcher");
                        client.DownloadFile(zipUrl, tempZip);
                    }

                    Console.WriteLine("[INFO] Extracting application files...");
                    Process p = new Process();
                    p.StartInfo.FileName = "powershell.exe";
                    p.StartInfo.Arguments = string.Format("-NoProfile -ExecutionPolicy Bypass -Command \"Expand-Archive -Path '{0}' -DestinationPath '{1}' -Force\"", tempZip, baseDir);
                    p.StartInfo.UseShellExecute = false;
                    p.Start();
                    p.WaitForExit();

                    if (File.Exists(tempZip)) File.Delete(tempZip);
                    Console.WriteLine("[OK] Application files extracted successfully!");
                    Console.WriteLine();
                }
                catch (Exception ex)
                {
                    Console.WriteLine("[ERROR] Could not auto-download package: " + ex.Message);
                    Console.WriteLine("Please download and extract 'PeopleCounter-v1.1.0-Windows.zip' manually.");
                    Console.WriteLine("Press any key to exit...");
                    Console.ReadKey();
                    return;
                }
            }

            // 3. Check if virtual environment is installed
            if (!File.Exists(venvPython))
            {
                Console.WriteLine("[NOTICE] First-time setup required. Running automated setup wizard...");
                Console.WriteLine();

                if (File.Exists(setupBat))
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
                    Console.WriteLine("[ERROR] Setup.bat not found in: " + baseDir);
                    Console.WriteLine("Press any key to exit...");
                    Console.ReadKey();
                    return;
                }

                if (!File.Exists(venvPython))
                {
                    Console.WriteLine();
                    Console.WriteLine("[ERROR] Setup did not complete successfully. Please run Setup.bat manually.");
                    Console.WriteLine("Press any key to exit...");
                    Console.ReadKey();
                    return;
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
