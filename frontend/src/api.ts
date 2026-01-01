import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
});

export interface TopStock {
    ticker: string;
    name: string;
    net_buy_amount: number;
    rank: number;
    percent_change?: number;
    close_price?: number;
}

export interface InvestorData {
    buy: TopStock[];
    sell: TopStock[];
    date?: string;
    consecutive?: TopStock[];
    new_inflow?: TopStock[];
    days_analyzed?: number;
    start_date?: string;
    end_date?: string;
}

export const getDailyData = async (date: string, investor: string): Promise<InvestorData> => {
    const response = await api.get('/data', {
        params: { date, investor },
    });
    return response.data;
};

export const getAdvancedAnalysis = async (days: number, investor: string): Promise<InvestorData> => {
    const response = await api.get('/analysis/advanced', {
        params: { days, investor },
    });
    return response.data;
};

export const getAnalysisData = async (days: number, investor: string): Promise<InvestorData> => {
    const response = await api.get('/analysis/trend', {
        params: { days, investor },
    });
    return response.data;
};

export const getDownloadUrl = (startDate: string, endDate: string, investors: string[]) => {
    const params = new URLSearchParams();
    params.append('start_date', startDate);
    params.append('end_date', endDate);
    investors.forEach(inv => params.append('investors', inv));
    return `http://localhost:8000/api/download?${params.toString()}`;
}
