import { NextResponse } from "next/server";
import { writeFile } from "fs/promises";
import path from "path";
import { spawn } from "child_process";
import yaml from "yaml";

// Helper function to run Python script
async function runPythonScript(configPath: string): Promise<any> {
    return new Promise((resolve, reject) => {
        const scriptPath = path.join(
            process.cwd(),
            "python",
            "process_campaign.py"
        );
        const pythonProcess = spawn("python", [
            scriptPath,
            "--config",
            configPath,
        ]);

        let stdout = "";
        let stderr = "";

        pythonProcess.stdout.on("data", (data) => {
            stdout += data.toString();
            console.log(`Python stdout: ${data}`);
        });

        pythonProcess.stderr.on("data", (data) => {
            stderr += data.toString();
            console.log(`Python stderr: ${data}`);
        });

        pythonProcess.on("close", (code) => {
            console.log("Python process completed with code:", code);
            console.log("stdout:", stdout);
            console.log("stderr:", stderr);

            if (code !== 0) {
                reject(
                    new Error(`Python script failed (code ${code}): ${stderr}`)
                );
            } else {
                try {
                    // Try to parse stdout as JSON
                    const result = JSON.parse(stdout);
                    resolve(result);
                } catch (e) {
                    console.error("Failed to parse Python output as JSON:", e);
                    resolve({ stdout, stderr });
                }
            }
        });
    });
}

export async function POST(request: Request) {
    try {
        const formData = await request.formData();
        const file: File | null = formData.get("file") as unknown as File;
        const primaryEmails = JSON.parse(
            formData.get("primaryEmails") as string
        );
        const ccEmails = JSON.parse(formData.get("ccEmails") as string);

        if (!file) {
            return NextResponse.json(
                { success: false, message: "No file uploaded" },
                { status: 400 }
            );
        }

        // Create necessary directories
        const uploadsDir = path.join(process.cwd(), "data", "uploads");
        const configDir = path.join(process.cwd(), "data", "config");
        const outputDir = path.join(process.cwd(), "data", "output");

        // Generate unique filename
        const timestamp = new Date().toISOString().replace(/[^0-9]/g, "");
        const filename = `campaign_report_${timestamp}.csv`;
        const filepath = path.join(uploadsDir, filename);

        // Write the uploaded file
        const bytes = await file.arrayBuffer();
        const buffer = Buffer.from(bytes);
        await writeFile(filepath, buffer);

        // Create config file for this run
        const configData = {
            input_offsite_csv: filepath,
            output_dir: outputDir,
            email_config: {
                sender_email: process.env.EMAIL_SENDER,
                sender_password: process.env.EMAIL_SENDER_PASSWORD,
                smtp_server:
                    process.env.EMAIL_SMTP_SERVER || "smtp.office365.com",
                smtp_port: parseInt(process.env.EMAIL_SMTP_PORT || "587"),
                primary_recipients: primaryEmails,
                cc_recipients: ccEmails,
            },
        };

        const configPath = path.join(configDir, `config_${timestamp}.yaml`);
        await writeFile(configPath, yaml.stringify(configData));

        console.log("Running Python script with config:", configPath);
        const result = await runPythonScript(configPath);
        console.log("Python script result:", result);

        if (!result.success) {
            throw new Error(result.error || "Python script failed");
        }

        return NextResponse.json({
            success: true,
            data: result,
        });
    } catch (error) {
        console.error("Error processing report:", error);
        return NextResponse.json(
            {
                success: false,
                message:
                    error instanceof Error
                        ? error.message
                        : "Failed to process report",
            },
            { status: 500 }
        );
    }
}
