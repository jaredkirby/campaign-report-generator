const { execSync } = require("child_process");
const path = require("path");
const fs = require("fs");

// Ensure Python environment is set up
try {
    // Create data directories
    const dirs = ["uploads", "output", "history", "config"].map((dir) =>
        path.join(process.cwd(), "data", dir)
    );

    dirs.forEach((dir) => {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    });

    // Check if we're in Vercel environment
    if (process.env.VERCEL) {
        console.log("Installing Python in Vercel environment...");
        // Use Python from Vercel runtime
        execSync("python3.11 -m ensurepip", { stdio: "inherit" });
        execSync("python3.11 -m pip install --upgrade pip", {
            stdio: "inherit",
        });
        execSync("python3.11 -m pip install -r requirements.txt", {
            stdio: "inherit",
        });
    } else {
        // Local development environment
        console.log("Installing Python dependencies...");
        execSync("pip install -r requirements.txt", { stdio: "inherit" });
    }
} catch (error) {
    console.error("Error during build:", error);
    process.exit(1);
}
