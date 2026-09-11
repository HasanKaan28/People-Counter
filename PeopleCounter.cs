using System;
using System.Diagnostics;
using System.IO;
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

            // Check if virtual environment is installed
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
