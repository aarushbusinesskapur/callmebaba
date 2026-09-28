import pandas as pd
from typing import Tuple, List

class DataSplitter:
    """Handles strict data splitting to prevent overfitting and look-ahead bias."""
    
    @staticmethod
    def standard_split(df: pd.DataFrame, train_pct: float = 0.6, val_pct: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Splits data chronologically into Train, Validation, and Final Holdout (Test).
        The final holdout must remain completely unseen during strategy development.
        """
        if df.empty:
            return df, df, df
            
        n = len(df)
        train_end = int(n * train_pct)
        val_end = train_end + int(n * val_pct)
        
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()
        
        return train_df, val_df, test_df

    @staticmethod
    def walk_forward_split(df: pd.DataFrame, n_splits: int = 5, train_size_pct: float = 0.7) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Generates walk-forward splits.
        Returns a list of (train_df, val_df) tuples stepping forward in time.
        Useful for continuous out-of-sample validation.
        """
        splits = []
        if df.empty or n_splits <= 0:
            return splits
            
        n = len(df)
        step_size = int((n * (1 - train_size_pct)) / n_splits)
        base_train_size = int(n * train_size_pct)
        
        for i in range(n_splits):
            start_idx = i * step_size
            end_train = start_idx + base_train_size
            end_val = end_train + step_size
            
            if end_val > n:
                end_val = n
                
            train_df = df.iloc[start_idx:end_train].copy()
            val_df = df.iloc[end_train:end_val].copy()
            splits.append((train_df, val_df))
            
        return splits
