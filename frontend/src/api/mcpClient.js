import axios from "axios";

const mcpApi = axios.create({
  baseURL: import.meta.env.VITE_MCP_BASE_URL || "http://localhost:8000",
  timeout: Number(import.meta.env.VITE_MCP_TIMEOUT_MS || 30000),
});

async function executeMcpTool(name, input = {}) {
  const response = await mcpApi.post("/mcp/tools", {
    name,
    input,
  });
  return response.data;
}

export async function fetchProjectsViaMCP() {
  return executeMcpTool("get_projects", {});
}

export async function fetchSlackChannelHistoryViaMCP(input = {}) {
  return executeMcpTool("get_slack_channel_history", input);
}

export async function fetchSlackChannelsViaMCP(input = {}) {
  return executeMcpTool("get_slack_channels", input);
}

function normalizeValue(value) {
  return (value || "").toString().trim().toLowerCase();
}

function formatProjectSummary(project) {
  return {
    type: "project",
    id: project?.id || "",
    name: project?.name || "Unknown project",
    status: project?.status || "Unknown",
    owner: project?.owner || "Unknown",
  };
}

/**
 * True when the user wants a list/count of Slack channels (not message bodies).
 */
function wantsSlackChannelList(lower) {
  if (!/\bchannels?\b/i.test(lower)) return false;
  // e.g. "messages in #general" — handled by history intent
  if (/\bmessages?\b/i.test(lower) && /\b(in|on|from|for)\b/i.test(lower)) return false;

  const signals = [
    "how many",
    "how much",
    "count",
    "number of",
    "list",
    "show",
    "what are",
    "what is",
    "which",
    "available",
    "currently",
    "current",
    "active",
    "all ",
    "give me",
    "fetch",
    "get ",
    "get me",
    "display",
    "enumerate",
    "tell me",
    "do we have",
    "are there",
    "total",
    "exist",
    "slack workspace",
  ];
  return signals.some((s) => lower.includes(s));
}

/**
 * Extract channel name/id for conversation history from free-form prompts.
 */
function parseSlackHistoryChannel(query) {
  const hashMatch = query.match(/#\s*([a-zA-Z0-9_-]+)/);
  if (hashMatch?.[1] && /\b(messages?|history|chat|conversation)\b/i.test(query)) {
    return hashMatch[1].trim();
  }
  const patterns = [
    /messages?\s+(?:on\s+this|on|in|from)\s+(?:the\s+)?(?:slack\s+)?(?:channel\s+)?[#"]?([^\s?"#]+)[#"]?/i,
    /history\s+(?:on|of|in|from)\s+(?:the\s+)?(?:slack\s+)?(?:channel\s+)?[#"]?([^\s?"#]+)[#"]?/i,
    /(?:read|show|get|fetch|pull)\s+(?:me\s+)?(?:the\s+)?(?:recent\s+)?messages?\s+(?:from|in|on)\s+(?:the\s+)?(?:channel\s+)?[#"]?([^\s?"#]+)[#"]?/i,
    /channel\s+[#"]?([a-zA-Z0-9_-]+)[#"]?\s+(?:messages?|history)/i,
  ];
  for (const re of patterns) {
    const m = query.match(re);
    if (m?.[1]) {
      const ch = m[1].trim().replace(/[?.!,:;]+$/, "");
      if (ch.length > 0) return ch;
    }
  }
  const quoted = query.match(/"([^"]+)"/);
  if (quoted?.[1] && /\b(message|messages|history|slack)\b/i.test(query)) {
    return quoted[1].trim();
  }
  return null;
}

function parsePrompt(prompt) {
  const query = (prompt || "").trim();
  const lowerQuery = query.toLowerCase();

  if (!query) {
    return { type: "list" };
  }

  // Slack: messages / history for a specific channel (many phrasings)
  if (
    /\b(messages?|history|conversation|chat)\b/i.test(lowerQuery) &&
    (/\b(channel|slack)\b/i.test(lowerQuery) || /#\w+/i.test(query))
  ) {
    const ch = parseSlackHistoryChannel(query);
    if (ch) return { type: "slack_history_channel", channel: ch };
  }
  if (
    lowerQuery.includes("messages on this") ||
    lowerQuery.includes("messages on channel") ||
    lowerQuery.includes("messages in channel") ||
    lowerQuery.includes("history on") ||
    lowerQuery.includes("history of")
  ) {
    const quotedMatch = query.match(/(?:messages\s+(?:on\s+this|on|in)\s+(?:channel\s+)?)"([^"]+)"/i);
    if (quotedMatch?.[1]) {
      return { type: "slack_history_channel", channel: quotedMatch[1].trim() };
    }

    const plainMatch = query.match(/(?:messages\s+(?:on\s+this|on|in)\s+(?:channel\s+)?|history\s+(?:on|of)\s+)(.+)$/i);
    if (plainMatch?.[1]) {
      return { type: "slack_history_channel", channel: plainMatch[1].trim().replace(/[?.!]+$/, "") };
    }
  }

  // Slack: list / count channels (dynamic wording)
  if (wantsSlackChannelList(lowerQuery)) {
    return { type: "slack_channels" };
  }

  // Project status (flexible)
  if (/\bstatus\b/i.test(lowerQuery) && /\b(of|for)\b/i.test(lowerQuery)) {
    const quotedMatch = query.match(/status\s+(?:of|for)\s+"([^"]+)"/i);
    if (quotedMatch?.[1]) {
      return { type: "status", projectName: quotedMatch[1].trim() };
    }
    const looseMatch = query.match(/status\s+(?:of|for)\s+(.+)$/i);
    if (looseMatch?.[1]) {
      return { type: "status", projectName: looseMatch[1].trim().replace(/[?.!]+$/, "") };
    }
  }

  // Projects by owner
  if (/\bassigned\s+to\b/i.test(lowerQuery) || /\bprojects?\s+(for|owned\s+by)\b/i.test(lowerQuery)) {
    const quotedMatch = query.match(/assigned\s+to\s+"([^"]+)"/i);
    if (quotedMatch?.[1]) {
      return { type: "owner", ownerName: quotedMatch[1].trim() };
    }
    const looseAssigned = query.match(/assigned\s+to\s+(.+)$/i);
    if (looseAssigned?.[1]) {
      return { type: "owner", ownerName: looseAssigned[1].trim().replace(/[?.!]+$/, "") };
    }
    const forMatch = query.match(/projects?\s+(?:for|owned\s+by)\s+"([^"]+)"/i);
    if (forMatch?.[1]) return { type: "owner", ownerName: forMatch[1].trim() };
    const forLoose = query.match(/projects?\s+(?:for|owned\s+by)\s+(.+)$/i);
    if (forLoose?.[1]) {
      return { type: "owner", ownerName: forLoose[1].trim().replace(/[?.!]+$/, "") };
    }
  }

  if (lowerQuery.includes("list") && lowerQuery.includes("project")) {
    return { type: "list" };
  }

  if (lowerQuery.includes("convex")) {
    return { type: "list" };
  }

  // Slack workspace context without a specific channel → default history channel
  if (
    lowerQuery.includes("slack") &&
    (lowerQuery.includes("channel") ||
      lowerQuery.includes("message") ||
      lowerQuery.includes("history") ||
      lowerQuery.includes("budget") ||
      lowerQuery.includes("trial"))
  ) {
    return { type: "slack_history" };
  }

  return { type: "unknown" };
}

export async function queryProjectsViaMCP(prompt) {
  const intent = parsePrompt(prompt);
  const userPrompt = (prompt || "").trim();
  const toolName =
    intent.type === "slack_channels"
      ? "get_slack_channels"
      : intent.type === "slack_history" || intent.type === "slack_history_channel"
        ? "get_slack_channel_history"
        : "get_projects";

  const toolInput = {
    query:
      userPrompt ||
      (toolName === "get_slack_channels"
        ? "list out channel"
        : toolName === "get_slack_channel_history"
          ? "show channel history"
          : "list out projects"),
    feature: toolName === "get_projects" ? "project" : "slack",
  };

  if (intent.type === "slack_history_channel" && intent.channel) {
    toolInput.channel = intent.channel;
  }

  const toolResult = await executeMcpTool(toolName, toolInput);
  const chatData = toolResult?.data ?? {};
  const answer =
    chatData?.type === "complete" && typeof chatData?.response === "string"
      ? chatData.response
      : "No complete response from chat API.";

  return {
    projects: [],
    answer,
    details: [],
    intent: intent.type,
  };
}
