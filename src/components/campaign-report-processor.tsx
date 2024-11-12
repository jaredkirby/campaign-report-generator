// /src/app/components/campaign-report-processor.tsx

"use client";

import React, { useState, useEffect } from "react";
import {
  Upload,
  FileText,
  Mail,
  AlertCircle,
  CheckCircle2,
  Plus,
  X,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ReactMarkdown from "react-markdown";

type ProcessingStatus = "idle" | "ready" | "processing" | "success" | "error";

interface ProcessResult {
  success: boolean;
  message?: string;
  data?: {
    markdown_path?: string;
    email_path?: string;
    campaign_count?: number;
    changes_detected?: number;
  };
}

export function CampaignReportProcessor() {
  const [file, setFile] = useState<File | null>(null);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<ProcessingStatus>("idle");
  const [markdownContent, setMarkdownContent] = useState("");
  const [error, setError] = useState("");

  const [newPrimaryEmail, setNewPrimaryEmail] = useState("");
  const [newCCEmail, setNewCCEmail] = useState("");
  const [primaryEmails, setPrimaryEmails] = useState<string[]>([]);
  const [ccEmails, setCCEmails] = useState<string[]>([]);
  const [emailError, setEmailError] = useState("");

  useEffect(() => {
    const storedPrimary = localStorage.getItem("primaryEmails");
    const storedCC = localStorage.getItem("ccEmails");

    if (storedPrimary) setPrimaryEmails(JSON.parse(storedPrimary));
    if (storedCC) setCCEmails(JSON.parse(storedCC));
  }, []);

  useEffect(() => {
    localStorage.setItem("primaryEmails", JSON.stringify(primaryEmails));
    localStorage.setItem("ccEmails", JSON.stringify(ccEmails));
  }, [primaryEmails, ccEmails]);

  const validateEmail = (email: string): boolean => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const addEmail = (type: "primary" | "cc", email: string) => {
    setEmailError("");

    if (!email) {
      setEmailError("Please enter an email address");
      return;
    }

    if (!validateEmail(email)) {
      setEmailError("Please enter a valid email address");
      return;
    }

    if (type === "primary") {
      if (primaryEmails.includes(email) || ccEmails.includes(email)) {
        setEmailError("Email already exists in the lists");
        return;
      }
      setPrimaryEmails([...primaryEmails, email]);
      setNewPrimaryEmail("");
    } else {
      if (ccEmails.includes(email) || primaryEmails.includes(email)) {
        setEmailError("Email already exists in the lists");
        return;
      }
      setCCEmails([...ccEmails, email]);
      setNewCCEmail("");
    }
  };

  const removeEmail = (type: "primary" | "cc", email: string) => {
    if (type === "primary") {
      setPrimaryEmails(primaryEmails.filter((e) => e !== email));
    } else {
      setCCEmails(ccEmails.filter((e) => e !== email));
    }
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile && selectedFile.name.endsWith(".csv")) {
      setFile(selectedFile);
      setError("");
      setStatus("ready");
    } else {
      setError("Please select a valid CSV file");
      setFile(null);
      setStatus("idle");
    }
  };

  const processReport = async () => {
    if (!file || primaryEmails.length === 0) {
      setError("Please select a file and add at least one primary email recipient");
      return;
    }
  
    setProcessing(true);
    setProgress(0);
    setStatus("processing");
    setMarkdownContent("");
  
    try {
      // Show upload progress
      setProgress(20);
  
      // Validate file size for Vercel limits (max 50MB)
      if (file.size > 50 * 1024 * 1024) {
        throw new Error("File size exceeds 50MB limit");
      }
  
      const formData = new FormData();
      formData.append("file", file);
      formData.append("primaryEmails", JSON.stringify(primaryEmails));
      formData.append("ccEmails", JSON.stringify(ccEmails));
  
      // Add request timeout for Vercel's 10s limit
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 9500); // 9.5s timeout
  
      setProgress(40);
  
      const response = await fetch("/api/process", {
        method: "POST",
        body: formData,
        signal: controller.signal,
      }).finally(() => clearTimeout(timeout));
  
      setProgress(60);
  
      const result = await response.json() as ProcessResult;
      
      if (!result.success) {
        throw new Error(result.message || "Failed to process report");
      }
  
      setProgress(80);
  
      // Fetch the markdown content
      if (result.data?.markdown_path) {
        const filename = result.data.markdown_path.split("/").pop();
        if (!filename) {
          throw new Error("Invalid markdown filename");
        }
  
        // Add timeout for markdown fetch
        const mdController = new AbortController();
        const mdTimeout = setTimeout(() => mdController.abort(), 9500);
  
        try {
          const markdownResponse = await fetch(`/api/report/md/${filename}`, {
            signal: mdController.signal,
            headers: {
              'Cache-Control': 'no-cache',
              'Pragma': 'no-cache'
            }
          }).finally(() => clearTimeout(mdTimeout));
  
          if (!markdownResponse.ok) {
            const errorText = await markdownResponse.text();
            console.error('Markdown fetch error:', errorText);
            throw new Error(`Failed to fetch report: ${markdownResponse.statusText}`);
          }
  
          const content = await markdownResponse.text();
          
          // Validate content
          if (!content || content.trim().length === 0) {
            throw new Error("Received empty report content");
          }
  
          setMarkdownContent(content);
  
          // Log successful processing metrics
          if (result.data?.campaign_count) {
            console.log(`Processed ${result.data.campaign_count} campaigns`);
          }
          if (result.data?.changes_detected) {
            console.log(`Detected ${result.data.changes_detected} changes`);
          }
        } catch (err) {
          if (err instanceof Error && err.name === 'AbortError') {
            throw new Error("Report fetch timed out - please try again");
          }
          throw err;
        }
      } else {
        throw new Error("No report was generated");
      }
  
      setStatus("success");
      setProgress(100);
  
    } catch (err) {
      console.error("Error processing report:", err);
      
      // Handle specific error types
      let errorMessage = "An error occurred";
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          errorMessage = "Request timed out - please try again";
        } else if (err.message.includes("Failed to fetch")) {
          errorMessage = "Network error - please check your connection";
        } else {
          errorMessage = err.message;
        }
      }
      
      setError(errorMessage);
      setStatus("error");
      setProgress(0);
    } finally {
      setProcessing(false);
    }
  };

  const renderStatus = () => {
    switch (status) {
      case "ready":
        return (
          <Alert className="mb-4">
            <FileText className="h-4 w-4" />
            <AlertDescription>File selected: {file?.name}</AlertDescription>
          </Alert>
        );
      case "processing":
        return (
          <div className="space-y-4 mb-4">
            <Alert>
              <AlertDescription>Processing campaign report...</AlertDescription>
            </Alert>
            <Progress value={progress} className="w-full" />
          </div>
        );
      case "success":
        return (
          <Alert className="mb-4">
            <CheckCircle2 className="h-4 w-4 text-green-500" />
            <AlertDescription>
              Report processed and distributed successfully!
            </AlertDescription>
          </Alert>
        );
      case "error":
        return (
          <Alert variant="destructive" className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        );
      default:
        return null;
    }
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <CardTitle>Campaign Report Processor</CardTitle>
        <CardDescription>
          Upload a CSV report file to process and distribute campaign
          information
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Email Recipients Section */}
          <div className="space-y-4">
            <h3 className="text-lg font-medium">Email Recipients</h3>

            {emailError && (
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{emailError}</AlertDescription>
              </Alert>
            )}

            {/* Primary Recipients */}
            <div className="space-y-2">
              <Label>Primary Recipients</Label>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="Enter email address"
                  value={newPrimaryEmail}
                  onChange={(e) => setNewPrimaryEmail(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === "Enter") {
                      addEmail("primary", newPrimaryEmail);
                    }
                  }}
                />
                <Button
                  onClick={() => addEmail("primary", newPrimaryEmail)}
                  size="icon"
                >
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {primaryEmails.map((email) => (
                  <Badge
                    key={email}
                    variant="secondary"
                    className="flex items-center gap-1"
                  >
                    {email}
                    <button
                      onClick={() => removeEmail("primary", email)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>

            {/* CC Recipients */}
            <div className="space-y-2">
              <Label>CC Recipients</Label>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="Enter email address"
                  value={newCCEmail}
                  onChange={(e) => setNewCCEmail(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === "Enter") {
                      addEmail("cc", newCCEmail);
                    }
                  }}
                />
                <Button onClick={() => addEmail("cc", newCCEmail)} size="icon">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {ccEmails.map((email) => (
                  <Badge
                    key={email}
                    variant="secondary"
                    className="flex items-center gap-1"
                  >
                    {email}
                    <button
                      onClick={() => removeEmail("cc", email)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          <Separator />

          {/* File Upload Section */}
          <div className="flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-6 bg-muted/50">
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
              id="file-upload"
            />
            <label
              htmlFor="file-upload"
              className="flex flex-col items-center cursor-pointer"
            >
              <Upload className="h-8 w-8 mb-2 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                Click to upload or drag and drop
              </span>
              <span className="text-xs text-muted-foreground mt-1">
                CSV files only
              </span>
            </label>
          </div>

          {/* Status Display */}
          {renderStatus()}

          {/* Process Button */}
          <div className="flex justify-center">
            <Button
              onClick={processReport}
              disabled={!file || processing || primaryEmails.length === 0}
              className="w-full md:w-auto"
            >
              {processing ? (
                <span className="flex items-center">Processing...</span>
              ) : (
                <span className="flex items-center">
                  <Mail className="mr-2 h-4 w-4" />
                  Process and Distribute Report
                </span>
              )}
            </Button>
          </div>

          {/* Report Output */}
          {markdownContent && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Generated Report</CardTitle>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="rendered" className="w-full">
                  <TabsList>
                    <TabsTrigger value="rendered">Rendered</TabsTrigger>
                    <TabsTrigger value="source">Source</TabsTrigger>
                  </TabsList>
                  <TabsContent value="rendered" className="mt-4">
                    <ScrollArea className="h-[600px] w-full rounded-md border p-4">
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown>{markdownContent}</ReactMarkdown>
                      </div>
                    </ScrollArea>
                  </TabsContent>
                  <TabsContent value="source" className="mt-4">
                    <ScrollArea className="h-[600px] w-full rounded-md border p-4">
                      <pre className="whitespace-pre-wrap font-mono text-sm">
                        {markdownContent}
                      </pre>
                    </ScrollArea>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
