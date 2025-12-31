import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

export interface ChatResponse {
    response: string;
    memories: any[];
}

export const chatWithAgent = async (message: string, userId: string = 'user1'): Promise<ChatResponse> => {
    try {
        const response = await axios.post<ChatResponse>(`${API_BASE}/chat`, {
            message,
            user_id: userId
        });
        return response.data;
    } catch (error) {
        console.error("Chat error:", error);
        throw error;
    }
};

export const uploadReport = async (text: string, patientId: string, userId: string = 'user1') => {
    try {
        const response = await axios.post(`${API_BASE}/upload_report`, {
            report_text: text,
            patient_id: patientId,
            user_id: userId
        });
        return response.data;
    } catch (error) {
        console.error("Upload error:", error);
        throw error;
    }
};
