import pandas as pd
import numpy as np

def calculate_prize_pools(df):
    """
    Calculate TOTO prize pools based on the TOTO prize structure
    
    Args:
        df: DataFrame containing TOTO results
    
    Returns:
        DataFrame with added prize pool calculations
    """
    # Make a copy to avoid modifying the original DataFrame
    result_df = df.copy()
    
    # Define constants for TOTO prize structure
    # Based on https://online.singaporepools.com/en/lottery/toto-prize-structure
    
    ORDINARY_ENTRY_PRICE = 1.00  # $1 per entry
    CONTRIBUTION_RATE = 0.54  # 54% of sales goes to prize money
    
    # Prize group allocation percentage
    GROUP_1_ALLOCATION = 0.38  # 38% to Group 1
    GROUP_2_ALLOCATION = 0.08  # 8% to Group 2
    GROUP_3_ALLOCATION = 0.05  # 5.5% to Group 3
    GROUP_4_ALLOCATION = 0.03  # 3% to Group 4
    GROUP_5_ALLOCATION = 0.04  # 4% to Group 5
    GROUP_6_ALLOCATION = 0.205  # 20.5% to Group 6
    GROUP_7_ALLOCATION = 0.205  # 20.5% to Group 7
    
    # Calculate total number of winners for each draw
    result_df['total_winners'] = (
        result_df['group_1_winners'] +
        result_df['group_2_winners'] +
        result_df['group_3_winners'] +
        result_df['group_4_winners'] +
        result_df['group_5_winners'] +
        result_df['group_6_winners'] +
        result_df['group_7_winners']
    )
    
    # Backward calculate the estimated prize pool
    # This is a rough estimate based on the prize money and winner counts
    
    for idx, row in result_df.iterrows():
        # If Group 1 had no winners, we can estimate from Group 2
        # Formula: Group 2 Prize = (Prize Pool * GROUP_2_ALLOCATION) / Group 2 Winners
        
        if row['group_2_winners'] > 0:
            est_prize_pool_g2 = (row['group_2_prize'] * row['group_2_winners']) / GROUP_2_ALLOCATION
        else:
            est_prize_pool_g2 = np.nan
            
        # Similar calculations from other groups
        if row['group_3_winners'] > 0:
            est_prize_pool_g3 = (row['group_3_prize'] * row['group_3_winners']) / GROUP_3_ALLOCATION
        else:
            est_prize_pool_g3 = np.nan
            
        if row['group_4_winners'] > 0:
            est_prize_pool_g4 = (row['group_4_prize'] * row['group_4_winners']) / GROUP_4_ALLOCATION
        else:
            est_prize_pool_g4 = np.nan
            
        if row['group_5_winners'] > 0:
            est_prize_pool_g5 = (row['group_5_prize'] * row['group_5_winners']) / GROUP_5_ALLOCATION
        else:
            est_prize_pool_g5 = np.nan
            
        if row['group_6_winners'] > 0:
            est_prize_pool_g6 = (row['group_6_prize'] * row['group_6_winners']) / GROUP_6_ALLOCATION
        else:
            est_prize_pool_g6 = np.nan
            
        if row['group_7_winners'] > 0:
            est_prize_pool_g7 = (row['group_7_prize'] * row['group_7_winners']) / GROUP_7_ALLOCATION
        else:
            est_prize_pool_g7 = np.nan
        
        # Take the average of available estimates to get the most likely prize pool
        available_estimates = [
            est for est in [
                est_prize_pool_g2,
                est_prize_pool_g3,
                est_prize_pool_g4,
                est_prize_pool_g5,
                est_prize_pool_g6,
                est_prize_pool_g7
            ] if not np.isnan(est)
        ]
        
        if available_estimates:
            estimated_prize_pool = sum(available_estimates) / len(available_estimates)
        else:
            # If we can't calculate from winners, make a rough estimate based on typical 
            # TOTO sales (around 1-3 million entries per draw)
            estimated_prize_pool = 2_000_000 * ORDINARY_ENTRY_PRICE * CONTRIBUTION_RATE
        
        result_df.at[idx, 'estimated_prize_pool'] = estimated_prize_pool
        
        # Calculate expected Group 1 prize if there were winners (for jackpot analysis)
        expected_group1_prize = estimated_prize_pool * GROUP_1_ALLOCATION
        result_df.at[idx, 'expected_group1_prize'] = expected_group1_prize
        
        # Estimate total ticket sales
        estimated_sales = estimated_prize_pool / CONTRIBUTION_RATE
        result_df.at[idx, 'estimated_sales'] = estimated_sales
        
        # For draws where Group 1 had no winners, calculate the potential rollover amount
        # This becomes part of the next draw's Group 1 prize
        if row['group_1_winners'] == 0:
            result_df.at[idx, 'rollover_amount'] = expected_group1_prize
        else:
            result_df.at[idx, 'rollover_amount'] = 0
    
    return result_df
