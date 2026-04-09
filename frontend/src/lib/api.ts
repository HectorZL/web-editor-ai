import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
});

export const uploadFile = async (type: 'gameplay' | 'voice' | 'music' | 'logo', projectName: string, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/upload/${type}/${projectName}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const startProcess = async (projectName: string) => {
  return api.post(`/process/${projectName}`);
};

export const startAudioProcess = async (projectName: string) => {
  return api.post(`/process-audio/${projectName}`);
};

export const startSubtitlesProcess = async (projectName: string, language: string = "auto") => {
  return api.post(`/process-subtitles/${projectName}`, { language });
};


export const getJobStatus = async (jobId: string) => {
  return api.get(`/status/${jobId}`);
};
