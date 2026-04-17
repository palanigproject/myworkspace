import axios from "axios";

const mcpApi = axios.create({
  baseURL: import.meta.env.VITE_MCP_BASE_URL || "http://localhost:8000",
  timeout: 10000,
});

export async function fetchProjectsViaMCP() {
  const response = await mcpApi.post("/mcp/tools", {
    name: "get_projects",
    input: {},
  });
  return response.data;
}

function normalizeValue(value) {
  return (value || "").toString().trim().toLowerCase();
}

function formatProjectSummary(project) {
  return {
    id: project?.id || "",
    name: project?.name || "Unknown project",
    status: project?.status || "Unknown",
    owner: project?.owner || "Unknown",
  };
}

function parsePrompt(prompt) {
  const query = (prompt || "").trim();
  const lowerQuery = query.toLowerCase();

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

  return { type: "unknown" };
}

export async function queryProjectsViaMCP(prompt) {
  const result = await fetchProjectsViaMCP();
  const projects = result?.data?.projects ?? [];
  const intent = parsePrompt(prompt);

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
      'Try one of these prompts: 1) what is the status of "Groomer Incentive Phase 2" 2) What projects are assigned to "Praveen Selvam" 3) List out the projects.',
    details: [],
    intent: "unknown",
  };
}
