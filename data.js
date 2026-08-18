// Mock Database for Executive Recruitment Command Center
// Current Date Reference: 2026-06-29

const jobOpeningsData = [
  {
    id: "JOB-001",
    companyName: "Apex Global Tech",
    jobTitle: "Senior Frontend Engineer (React)",
    department: "Engineering",
    totalPositions: 3,
    targetHireDate: "2026-07-20",
    daysOpen: 18,
    status: "On Track",
    recruiter: "Sarah Jenkins",
    nextAction: "Schedule final technical round for finalist candidate by EOD.",
    sources: {
      naukri: 45,
      linkedin: 60,
      referral: 15,
      website: 10
    },
    pipeline: {
      screening: 42,
      interview: 18,
      offered: 2,
      rejected: 65,
      hired: 3
    }
  },
  {
    id: "JOB-002",
    companyName: "Nexus Software Systems",
    jobTitle: "Technical Product Manager",
    department: "Product Management",
    totalPositions: 1,
    targetHireDate: "2026-07-05",
    daysOpen: 28,
    status: "Delayed",
    recruiter: "David Smith",
    nextAction: "Follow up with VP of Product on compensation review.",
    sources: {
      naukri: 20,
      linkedin: 35,
      referral: 5,
      website: 8
    },
    pipeline: {
      screening: 22,
      interview: 8,
      offered: 1,
      rejected: 36,
      hired: 1
    }
  },
  {
    id: "JOB-003",
    companyName: "Apex Global Tech",
    jobTitle: "Senior Data Scientist (GenAI & LLMs)",
    department: "Data & AI",
    totalPositions: 2,
    targetHireDate: "2026-08-10",
    daysOpen: 8,
    status: "On Track",
    recruiter: "Sarah Jenkins",
    nextAction: "Source candidate shortlists specializing in PyTorch and transformer models.",
    sources: {
      naukri: 12,
      linkedin: 25,
      referral: 3,
      website: 2
    },
    pipeline: {
      screening: 15,
      interview: 4,
      offered: 0,
      rejected: 21,
      hired: 2
    }
  },
  {
    id: "JOB-004",
    companyName: "CloudScale Dynamics",
    jobTitle: "Lead DevOps Engineer (Kubernetes & AWS)",
    department: "Infrastructure",
    totalPositions: 2,
    targetHireDate: "2026-06-15",
    daysOpen: 45,
    status: "Delayed",
    recruiter: "Michael Green",
    nextAction: "Review JD requirements with Engineering Director; sourcing is currently stalled.",
    sources: {
      naukri: 62,
      linkedin: 85,
      referral: 2,
      website: 6
    },
    pipeline: {
      screening: 85,
      interview: 12,
      offered: 0,
      rejected: 58,
      hired: 0
    }
  },
  {
    id: "JOB-005",
    companyName: "Nexus Software Systems",
    jobTitle: "HR People Operations Lead",
    department: "Human Resources",
    totalPositions: 1,
    targetHireDate: "2026-07-25",
    daysOpen: 12,
    status: "On Track",
    recruiter: "Emma Watson",
    nextAction: "Conduct initial HR phone screenings for top 5 applicants.",
    sources: {
      naukri: 15,
      linkedin: 18,
      referral: 4,
      website: 11
    },
    pipeline: {
      screening: 14,
      interview: 6,
      offered: 0,
      rejected: 28,
      hired: 0
    }
  },
  {
    id: "JOB-006",
    companyName: "Vanguard Financial Technologies",
    jobTitle: "Enterprise Account Executive",
    department: "Sales",
    totalPositions: 2,
    targetHireDate: "2026-07-15",
    daysOpen: 15,
    status: "On Track",
    recruiter: "Emma Watson",
    nextAction: "Send formal offer letter to candidate.",
    sources: {
      naukri: 28,
      linkedin: 42,
      referral: 10,
      website: 5
    },
    pipeline: {
      screening: 30,
      interview: 15,
      offered: 1,
      rejected: 37,
      hired: 2
    }
  }
];

// Helper calculations to drive KPIs
function getSummaryMetrics(jobs = jobOpeningsData) {
  let totalActiveOpenings = jobs.length;
  let totalPositions = jobs.reduce((sum, j) => sum + j.totalPositions, 0);
  
  let totalApplied = jobs.reduce((sum, j) => {
    return sum + (j.sources.linkedin || 0) + (j.sources.referral || 0) + (j.sources.website || 0);
  }, 0);

  let sourceTotals = {
    linkedin: jobs.reduce((sum, j) => sum + (j.sources.linkedin || 0), 0),
    referral: jobs.reduce((sum, j) => sum + (j.sources.referral || 0), 0),
    website: jobs.reduce((sum, j) => sum + (j.sources.website || 0), 0),
  };

  let pipelineTotals = {
    screening: jobs.reduce((sum, j) => sum + j.pipeline.screening, 0),
    interview: jobs.reduce((sum, j) => sum + j.pipeline.interview, 0),
    offered: jobs.reduce((sum, j) => sum + j.pipeline.offered, 0),
    rejected: jobs.reduce((sum, j) => sum + j.pipeline.rejected, 0),
    hired: jobs.reduce((sum, j) => sum + j.pipeline.hired, 0),
  };

  let averageDaysOpen = jobs.length > 0
    ? Math.round(jobs.reduce((sum, j) => sum + j.daysOpen, 0) / jobs.length)
    : 0;

  let delayedJobsCount = jobs.filter(j => j.status === "Delayed").length;
  let delayedOver20DaysCount = jobs.filter(j => j.daysOpen > 20).length;

  return {
    totalActiveOpenings,
    totalPositions,
    totalApplied,
    sourceTotals,
    pipelineTotals,
    averageDaysOpen,
    delayedJobsCount,
    delayedOver20DaysCount
  };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { jobOpeningsData, getSummaryMetrics };
}
