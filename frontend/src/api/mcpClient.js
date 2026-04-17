import axios from "axios";

const mcpApi = axios.create({
  baseURL: import.meta.env.VITE_MCP_BASE_URL || "http://localhost:8000",
  timeout: 10000,
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

function parsePrompt(prompt) {
  const query = (prompt || "").trim();
  const lowerQuery = query.toLowerCase();
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

  if (
    lowerQuery.includes("channels available") ||
    lowerQuery.includes("channels are currently") ||
    lowerQuery.includes("channels currently") ||
    (lowerQuery.includes("what are the channels") && !lowerQuery.includes("messages")) ||
    lowerQuery.includes("list channels")
  ) {
    return { type: "slack_channels" };
  }


  if (!query) {
    return { type: "list" };
  }

  if (lowerQuery.includes("status of")) {
    const quotedMatch = query.match(/status\s+of\s+"([^"]+)"/i);
    if (quotedMatch?.[1]) {
      return { type: "status", projectName: quotedMatch[1].trim() };
    }

    const looseMatch = query.match(/status\s+of\s+(.+)$/i);
    if (looseMatch?.[1]) {
      return { type: "status", projectName: looseMatch[1].trim().replace(/[?.!]+$/, "") };
    }
  }

  if (lowerQuery.includes("assigned to")) {
    const quotedMatch = query.match(/assigned\s+to\s+"([^"]+)"/i);
    if (quotedMatch?.[1]) {
      return { type: "owner", ownerName: quotedMatch[1].trim() };
    }

    const looseMatch = query.match(/assigned\s+to\s+(.+)$/i);
    if (looseMatch?.[1]) {
      return { type: "owner", ownerName: looseMatch[1].trim().replace(/[?.!]+$/, "") };
    }
  }

  if (lowerQuery.includes("list") && lowerQuery.includes("project")) {
    return { type: "list" };
  }

  if (lowerQuery.includes("convex")) {
    return { type: "list" };
  }

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

  if (intent.type === "slack_channels") {
    const channelsResult = await fetchSlackChannelsViaMCP({});
    const channelsData = channelsResult?.data?.result?.channels ?? {};
    const channels = Array.isArray(channelsData?.channels) ? channelsData.channels : [];
    const details = channels.map((channel, index) => ({
      type: "slack_channel",
      id: channel?.id || `${index}`,
      name: channel?.name || "unknown-channel",
      topic: channel?.topic?.value || "",
      purpose: channel?.purpose?.value || "",
      members_count: channel?.num_members ?? 0,
      is_private: Boolean(channel?.is_private),
    }));

    if (channelsData?.ok !== true) {
      return {
        projects: [],
        answer: `Unable to fetch Slack channels: ${channelsData?.error || "Unknown Slack API error"}.`,
        details: [],
        intent: "slack_channels",
      };
    }

    return {
      projects: [],
      answer: `There are ${details.length} active Slack channel(s) currently available.`,
      details,
      intent: "slack_channels",
    };
  }

  if (intent.type === "slack_history" || intent.type === "slack_history_channel") {
    const toolInput = intent.type === "slack_history_channel" ? { channel: intent.channel } : {};
    const slackResult = await fetchSlackChannelHistoryViaMCP(toolInput);
    const history = slackResult?.data?.result?.history ?? {};
    const messages = Array.isArray(history?.messages) ? history.messages : [];
    const details = messages.map((message, index) => ({
      type: "slack_message",
      id: message?.ts || `${index}`,
      user: message?.user || message?.username || message?.bot_id || "Unknown",
      text: message?.text || "(no text)",
      ts: message?.ts || "",
      subtype: message?.subtype || "",
    }));

    if (history?.ok !== true) {
      return {
        projects: [],
        answer: `Unable to fetch Slack channel history: ${history?.error || "Unknown Slack API error"}.`,
        details: [],
        intent: intent.type,
      };
    }

    return {
      projects: [],
      answer:
        intent.type === "slack_history_channel"
          ? `Fetched ${details.length} message(s) from Slack channel ${intent.channel}.`
          : `Fetched ${details.length} Slack message(s) from the configured channel.`,
      details,
      intent: intent.type,
    };
  }

  const result = await fetchProjectsViaMCP();
  const projects = result?.data?.projects ?? [];

  if (intent.type === "list") {
    const details = projects.map((project) => formatProjectSummary(project));
    return {
      projects,
      answer: `Here are ${projects.length} project(s) currently available.`,
      details,
      intent: "list",
    };
  }

  if (intent.type === "status") {
    const targetName = normalizeValue(intent.projectName);
    const exact = projects.find((project) => normalizeValue(project.name) === targetName);
    const matched = exact
      ? [exact]
      : projects.filter((project) => normalizeValue(project.name).includes(targetName));

    if (matched.length === 0) {
      return {
        projects: [],
        answer: `I could not find a project named ${intent.projectName}.`,
        details: [],
        intent: "status",
      };
    }

    if (matched.length === 1) {
      const project = matched[0];
      return {
        projects: matched,
        answer: `The status of ${project.name} is ${project.status || "Unknown"}.`,
        details: [formatProjectSummary(project)],
        primary: formatProjectSummary(project),
        intent: "status",
      };
    }

    return {
      projects: matched,
      answer: `I found ${matched.length} projects matching ${intent.projectName}. Please pick one for an exact status.`,
      details: matched.map((project) => formatProjectSummary(project)),
      intent: "status",
    };
  }

  if (intent.type === "owner") {
    const targetOwner = normalizeValue(intent.ownerName);
    const matched = projects.filter((project) => normalizeValue(project.owner).includes(targetOwner));

    if (matched.length === 0) {
      return {
        projects: [],
        answer: `I could not find projects assigned to ${intent.ownerName}.`,
        details: [],
        intent: "owner",
      };
    }

    return {
      projects: matched,
      answer: `Projects assigned to ${intent.ownerName} are listed below.`,
      details: matched.map((project) => formatProjectSummary(project)),
      intent: "owner",
    };
  }

  return {
    projects,
    answer:
      'Try one of these prompts: 1) what is the status of "Groomer Incentive Phase 2" 2) What projects are assigned to "Praveen Selvam" 3) List out the projects 4) What are the channels available 5) What are the messages on this "general".',
    details: [],
    intent: "unknown",
  };
}
