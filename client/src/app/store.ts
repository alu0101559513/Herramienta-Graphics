import { configureStore } from '@reduxjs/toolkit';
import { authReducer } from '../features/auth/auth.slice';
import { analysisReducer } from '../features/analysis/analysis.slice';
export const store = configureStore({
  reducer: {
    auth: authReducer,
    analysis: analysisReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
