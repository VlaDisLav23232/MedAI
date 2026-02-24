export const ROUTES = {
  home: "/",
  agent: "/agent",
  patients: "/patients",
  admin: "/admin",
  profile: "/profile",
  login: "/auth/login",
  register: "/auth/register",
  timeline: (patientId: string) => `/timeline/${patientId}`,
  caseReport: (reportId: string) => `/case/${reportId}`,
};

export const STORAGE_KEYS = {
  authUser: "medai.auth.user",
  authToken: "medai.auth.token",
};
